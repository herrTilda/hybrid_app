import os
import json
import pandas as pd
import numpy as np
import streamlit as st
import math 

# testing testing

# Install sund in a custom location
import subprocess
import sys
if "sund" not in os.listdir('./custom_package'):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--target=./custom_package", 'https://isbgroup.eu/edu/assets/sund-1.0.1.tar.gz#sha256=669a1d05c5c8b68500086e183d831650277012b3ea57e94356de1987b6e94e3e'])

sys.path.append('./custom_package')
import sund

st.elements.utils._shown_default_value_warning=True # This is not a good solution, but it hides the warning of using default values and sessionstate api

# Setup the models

def setup_model(model_name):
    sund.installModel(f"./models/{model_name}.txt")
    model_class = sund.importModel(model_name)
    model = model_class() 

    fs = []
    for path, subdirs, files in os.walk('./results'):
        for name in files:
            if model_name in name.split('(')[0] and "ignore" not in path:
                fs.append(os.path.join(path, name))
    fs.sort()
    with open(fs[0],'r') as f:
        param_in = json.load(f)
        params = param_in['x']

    model.parametervalues = params
    features = model.featurenames
    return model, features

model, model_features = setup_model('alcohol_model')

# Define functions needed

def flatten(list):
    return [item for sublist in list for item in sublist]

def simulate(m, anthropometrics, stim, extra_time = 10):
    act = sund.Activity(timeunit = 'days')
    pwc = sund.PIECEWISE_CONSTANT # space saving only
    const = sund.CONSTANT # space saving only

    for key,val in stim.items():
        act.AddOutput(name = key, type=pwc, tvalues = val["t"], fvalues = val["f"]) 
    for key,val in anthropometrics.items():
        act.AddOutput(name = key, type=const, fvalues = val) 
    
    sim = sund.Simulation(models = m, activities = act, timeunit = 'days')
    
    sim.ResetStatesDerivatives()
    t_start = min(stim["EIchange"]["t"]+stim["BP_med"]["t"])-0.25 # -0.25??

    sim.Simulate(timevector = np.linspace(t_start, max(stim["EIchange"]["t"])+extra_time, 10000))
    
    sim_results = pd.DataFrame(sim.featuredata,columns=sim.featurenames)
    sim_results.insert(0, 'Time', sim.timevector)

    t_start_diet = min(stim["EIchange"]["t"])-0.25

    sim_diet_results = sim_results[(sim_results['Time']>=t_start_diet)]
    return sim_diet_results

# Start the app

st.title("Simulation weight change")
st.markdown("""Using the model for insulin resistance and blood pressure, you can simulate the dynamics of different changes in energy intake and blood pressure medication based on custom anthropometrics. 

Below, you can specify how big change in energy intake you want to simulate and when/how big meals to simulate.

""")
   
# Anthropometrics            
st.subheader("Anthropometrics")
    

if 'sex' not in st.session_state:
    st.session_state['sex'] = 'Man'
if 'weight' not in st.session_state:
    st.session_state['weight'] = 90.0
st.session_state['ECFinit'] = 0.7*0.235*st.session_state['weight']    
if 'Finit' not in st.session_state:
    if st.session_state['sex']== 'Woman':
        st.session_state['Finit'] = (st.session_state['weight']/100)*(0.14*st.session_state['age'] + 39.96*math.log(st.session_state['weight']/((0.01*st.session_state['height'])^2)) - 102.01)
    elif st.session_state['sex']== 'Man': 
        st.session_state['fat'] = (st.session_state['weight']/100)*(0.14*st.session_state['age'] + 37.31*math.log(st.session_state['weight']/((0.01*st.session_state['height'])^2)) - 103.95) 
if 'Linit' not in st.session_state:
    st.session_state['Ginit'] = (1 + 2.7)*0.5
    st.session_state['lean'] = st.session_state['weight'] - (st.session_state['fat'] + (1 + 2.7)*st.session_state['Ginit'] + st.session_state['ECFinit'])
else:
    st.session_state['Ginit'] = st.session_state['weight'] - (st.session_state['fat'] + (1 + 2.7)*st.session_state['Ginit'] + st.session_state['ECFinit'])

if 'height' not in st.session_state:
    st.session_state['height'] = 185
if 'age' not in st.session_state:
    st.session_state['age'] = 50

st.session_state['meal'] = 0

anthropometrics = {"sex": st.session_state['sex'], "weight": st.session_state['weight'], "height": st.session_state['height']}
anthropometrics["sex"] = st.selectbox("Sex:", ["Man", "Woman"], ["Man", "Woman"].index(st.session_state['sex']), key="sex")
anthropometrics["weight"] = st.number_input("Weight (kg):", 0.0, 1000.0, st.session_state.weight, 0.1, key="weight") # max, min # 0.1?
anthropometrics["Finit"] = st.number_input("Fat mass (kg):", 0.0, 1000.0, st.session_state.weight, 0.1, key="fat") # max, min
anthropometrics["Linit"] = st.number_input("Lean mass (kg):", 0.0, 1000.0, st.session_state.weight, 0.1, key="lean") # max, min
anthropometrics["height"] = st.number_input("Height (m):", 0.0, 2.5, st.session_state.height, key="height")
anthropometrics["age"] = st.number_input("Age (years):", 0.0, 200, st.session_state.age, key="age")

anthropometrics["sex"] = float(anthropometrics["sex"].lower() in ["male", "man", "men", "boy", "1", "chap", "guy"]) #Converts to a numerical representation

# Specifying diet
st.subheader("Diet")

diet_time = []
diet_kcals = []
diet_length = []
BPmed_time = []

st.divider()
start_time = st.session_state['age']

st.markdown(f"**Blood pressure medication {i+1}**")

diet_time.append(st.number_input("TStart of diet (age): ", 0.0, 100.0, start_time, 0.1, key=f"diet_time{i}"))
diet_length.append(st.number_input("Diet length (years): ", 0.0, 240.0, 20.0, 0.1, key=f"diet_length{i}"))
diet_kcals.append(st.number_input("Change in kcal of diet (kcal): ", 0.0, 1000.0, 45.0, 1.0, key=f"diet_kcals{i}"))
BPmed_time.append(st.number_input("Start of blood pressure medication (age): ", start_time, key=f"BPmed_time{i}"))
start_time += 1
st.divider()


EIchange = [0]+[c*on for c in diet_kcals for on in [1 , 0]]
diet_length = [0]+[t*on for t in diet_length for on in [1 , 0]]

t_long = [t_long+(l/60)*on for t_long,l in zip(diet_time, diet_length) for on in [0,1]]


st.subheader(f"Specifying meals")

start_time = 0

meal_times = []
meal_kcals = []

n_meals = st.slider("Number of (solid) meals:", 0, 5, 1)

for i in range(n_meals):
    st.markdown(f"**Meal {i+1}**")
    meal_times.append(st.number_input("Start of meal simulations (years): ", 0.0, diet_length, 0.1, key=f"meal_times{i}"))
    meal_kcals.append(st.number_input("Change in kcal of diet (kcal): ", 78000, key=f"diet_kcals{i}"))
    meal_amount = meal_kcals/4*1000 # converting from kcal to mg glucose
    start_time += 0.1
    st.divider()
if n_meals < 1.0:
    st.divider()

meal_amount = [0]+[k*on for k in meal_amount for on in [1 , 0]]
meal_times = [0]+[n*on for n in meal_times for on in [1 , 0]]

t_meal = [t_meal+(l/60)*on for t_meal,l in zip(meal_times, 0.3) for on in [0,1]]

# Setup stimulation to the model

stim_long = {
    "EIchange": {"t": diet_time, "f": EIchange},
    "meal": {"t": t_meal, "f": 0}
    }

stim_meal = {
    "meal_amount": {"t": t_meal, "f": meal_amount},
    "meal": {"t": t_meal, "f": 1}
    }

# Plotting the drinks

sim_long = simulate(model, anthropometrics, stim_long, extra_time=extra_time)
sim_meal = simulate(model, anthropometrics, stim_meal, extra_time=extra_time)

st.subheader("Plotting long term simulation of weight change")

feature = st.selectbox("Feature of the model to plot", model_features)
st.line_chart(sim_long, x="Time", y=feature)

st.subheader("Plotting meal simulations based on time points chosen in long term simulation")
feature = st.selectbox("Feature of the model to plot", model_features)
st.line_chart(sim_meal, x="Time", y=feature)