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

model, model_features = setup_model('bloodpressure_model')

# Define functions needed

def flatten(list):
    return [item for sublist in list for item in sublist]

def simulate(m, anthropometrics, stim):
    act = sund.Activity(timeunit = 'days')
    pwc = sund.PIECEWISE_CONSTANT # space saving only
    const = sund.CONSTANT # space saving only

    for key,val in stim.items():
        act.AddOutput(name = key, type=pwc, tvalues = val["t"], fvalues = val["f"]) 
    for key,val in anthropometrics.items():
        act.AddOutput(name = key, type=const, fvalues = val) 
    
    sim = sund.Simulation(models = m, activities = act, timeunit = 'days')
    
    sim.ResetStatesDerivatives()
    t_start = min(stim["BPmed_time"]["t"])

    sim.Simulate(timevector = np.linspace(t_start, max(stim["BPmed_time"]["t"]), 10000))
    
    sim_results = pd.DataFrame(sim.featuredata,columns=sim.featurenames)
    sim_results.insert(0, 'Time', sim.timevector)

    return sim_results

# Start the app

st.title("Simulation of blood pressure change")
st.markdown("""Your blood pressure changes as you age, and can be lowered using different blood pressure medications.

Below, you can specify for how long you want to simulate and if you want to take a blood pressure medication or not.

""")

if 'age' not in st.session_state:
    st.session_state['age'] = 40
anthropometrics = {st.session_state['age']}

# Specifying blood pressure medication
st.subheader("Blood pressure")

BPmed_time = 0
t_long = []

st.divider()

if 'age' not in st.session_state:
    st.session_state['age'] = 40
start_time = st.session_state['age']

BPmed_time = st.number_input("Start of blood pressure medication (age): ", 40.0, 100.0, key="BPmed_time")
t_long = st.number_input("How long to simulate (years): ", 0.0, 200.0, 40.0, key="t_long")

BPmed_time = [0] + BPmed_time + [0]
t_long = st.session_state['age'] + BPmed_time + t_long

st.divider()


# Setup stimulation to the model

stim = {
    "BPmed_time": {"t": t_long, "f": BPmed_time}
    }

# Plotting blood pressure 

sim = simulate(model, anthropometrics, stim)

st.subheader("Plotting blood pressure over time")

feature = st.selectbox("Feature of the model to plot", model_features)
st.line_chart(sim, x="Time", y=feature)

