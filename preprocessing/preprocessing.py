import os
import sys
import re
import threading
import pyedflib
import pandas as pd

from collections import deque
from pathlib import Path

sys.path.append('..')
from utils import SAMPLE_FREQ, CircularEncoder, print_status
sys.path.remove('..')

database_path = Path('..', 'sleep-edf-database-expanded-1.0.0')

get_edf_dir_name = lambda study_name: 'sleep-' + study_name
get_subject_filename = lambda study_name: 'S' + study_name[0].upper() \
+ '-subjects.xls'

def preprocess_cassette_subject_data(data):
    # Rename columns
    data = data.rename(columns={
        'k': 'subject',
        'sex (F=1)': 'sex',
        'LightsOff': 'lights_off'
    })
    
    # Make sex labels readable
    data['sex'] = data['sex'].astype(str)

    data.loc[data['sex'] == '0', 'sex'] = 'M'
    data.loc[data['sex'] == '1', 'sex'] = 'F'

    return data

def preprocess_telemetry_subject_data(data):
    return data

def preprocess_subject_data(study_name):
    print(f'Preprocessing {study_name} subject data...', '\r')

    # Get subject data
    data = pd.read_excel(database_path / get_subject_filename(study_name))
    match study_name:
        case 'cassette':
            data = preprocess_cassette_subject_data(data)
        case 'telemetry':
            data = preprocess_telemetry_subject_data(data)
    
    # Circularize time
    time_encoder = CircularEncoder()
    
    data['lights_off'] = data['lights_off'].apply(
            lambda t: (t.hour + t.minute/60)/24)
    data['lights_off_cos'], data['lights_off_sin'] = \
                time_encoder.transform(cassette_data['lights_off'])
    del data['lights_off']

    # Get edf directory name
    edf_dir_name = get_edf_dir_name(study_name)

    # Get PSG filenames
    psg_filenames = [s for s in os.listdir(
        database_path / edf_dir_name) if 'PSG' in s]
    psg_filenames.sort(key=lambda s: int(s[3:6]))
    data['psg_filename'] = psg_filenames

    # Get hypnogram filenames
    hypnogram_filenames = [s for s in os.listdir(
            database_path / edf_dir_name) if 'Hypnogram' in s]
    hypnogram_filenames.sort(key=lambda s: int(s[3:6]))
    data['hypnogram_filename'] = hypnogram_filenames
    
    # Get technicians
    data['technician'] = [s[7] for s in data['hypnogram_filename']]

    print(f'{study_name.capitalize()} subject data processed successfully')
    return data

# Signal data preprocessing steps:
# Iterate through each whole night
# --- Unpack filenames
def get_signal_data(data, study_name, edf_dir_name):
    # Add EEG signal data
    temp_data = []
    n_nights = len(data)

    for night_idx, base_row in data.iterrows():
        # Unpack filenames before converting base row to python list
        psg_filename = base_row['psg_filename']
        hypnogram_filename = base_row['hypnogram_filename']
        
        # Adjust min and max frequencies with LP and HP prefilter frequencies
        min_freq = global_min_freq
        max_freq = global_max_freq

        prefilter_text = pyedflib.highlevel.read_edf(str(cassette_path / psg_filename))[1][0]['prefilter']
        
        LP_freq = re.search(r'LP:([\d.]+)', prefilter_text)
        if LP_freq != None:
            LP_freq = float(LP_freq.group(1))
            max_freq = LP_freq if LP_freq < global_max_freq else global_max_freq
        
        HP_freq = re.search(r'HP:([\d.]+)', prefilter_text)
        if HP_freq != None:
            HP_freq = float(HP_freq.group(1))
            min_freq = HP_freq if HP_freq > global_min_freq else global_min_freq
        
        # Add data for each annotation
        annotations = pyedflib.highlevel.read_edf_header(str(cassette_path / hypnogram_filename))['annotations']
        n_stages = len(annotations) - 1

        base_row = base_row.tolist()

        for stage_idx, annotation in enumerate(annotations[:-1]):
            # Print status
            status = f'[preprocessing.py]: Processing night {night_idx}/{n_nights}, stage {stage_idx}/{n_stages}'
            status_deque.append(status)

            # Indices for signal reading
            start_index = int(annotation[0])
            end_index = start_index + int(annotation[1])
            
            # Check for short-duration sleep stages
            duration_freq = SAMPLE_FREQ/int(annotation[1])
            min_freq = max(min_freq, duration_freq)
            
            # Sleep stage label
            label = annotation[-1][-1]

            # Add this data point
            new_row = base_row[:]
            new_row.extend((start_index, end_index, min_freq, max_freq, label))
            cassette_data_temp.append(new_row)

    # End status printing thread
    status_deque.append(end_var)
    status_thread.join()

    # Reconstruct dataframe
    column_names = cassette_data.columns.tolist()
    column_names.extend(('start_index', 'end_index', 'min_freq', 'max_freq', 'label'))

    cassette_data = pd.DataFrame(cassette_data_temp, columns=column_names)

    # Add indicator for cassette/telemetry study
    cassette_data['study'] = 0

# Create cassette and telemetry data
if __name__ == '__main__':
    cassette_data = preprocess_subject_data('cassette')
    print(cassette_data)

'''
telemetry_data = create_telemetry_data()

# Save data
path = Path('../data')
X.to_csv(path / 'X.csv', index=False)
y.to_csv(path / 'y.csv', index=False)
y_extras.to_csv(path / 'y_extras.csv', index=False)
'''
