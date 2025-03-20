import os
import pyedflib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from circular_encoder import CircularEncoder

time_norm = lambda time: (time.hour + time.minute/60)/24
time_cos = lambda time: np.cos(2*np.pi*time_norm(time))
time_sin = lambda time: np.sin(2*np.pi*time_norm(time))

# Delta: <3.5 Hz
# Theta: 4-7.5 Hz
# Alpha: 8-13 Hz
# Beta: 14-30 Hz
# Gamma >30 Hz

### Cassette Data

# Get subject data
cassette_subject_data_path = os.path.join('sleep-edf-database-expanded-1.0.0', 'SC-subjects.xls')
cassette_data = pd.read_excel(cassette_subject_data_path)

# Preprocess columns
cassette_data = cassette_data.rename(columns={'k': 'subject', 'sex (F=1)': 'sex', 'LightsOff': 'lights_off'}) # rename columns to be machine readable
cassette_data['sex'] = cassette_data['sex'] - 1

# Circularize time
time_encoder = CircularEncoder()

cassette_data['lights_off'] = cassette_data['lights_off'].apply(lambda t: (t.hour + t.minute/60)/24)
cassette_data['lights_off_cos'], cassette_data['lights_off_sin'] = time_encoder.transform(cassette_data['lights_off'])
del cassette_data['lights_off']

# Add EEG signal data

'''
file = cassette_hypnograms_1[0]
x = pyedflib.highlevel.read_edf_header(file)
x = x['annotations']

x = pyedflib.EdfReader(file)
x = x.getSignalHeaders()
'''

# Add hypnogram data
#
# Delta: <3.5 Hz
# Theta: 4-7.5 Hz
# Alpha: 8-13 Hz
# Beta: 14-30 Hz
# Gamma >30 Hz

# Add indicator for cassette data

### Compute real fourier transform
# from scipy.fft import rfft, rfftfreq
#
# def ft(x, f_s):
#     f = rfftfreq(len(x), 1/f_s)
#     A = 2*np.abs(rfft(x))/len(x)
#
#     return f, A
#
# Sample plot of a signal
# f, A = ft(sig, 100)
# plt.plot(f, A)
# plt.show()
