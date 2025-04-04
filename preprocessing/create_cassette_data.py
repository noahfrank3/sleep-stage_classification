import os
import sys
import re
import threading
import pyedflib
import pandas as pd

sys.path.append('..')

from pathlib import Path
from collections import deque
from utils import SAMPLE_FREQ, CircularEncoder, print_status

def create_cassette_data():
    # Create path labels
    database_path = Path('..', 'sleep-edf-database-expanded-1.0.0')
    cassette_path = database_path / 'sleep-cassette'

    # Least conservative bounds for minimum and maximum frequency
    global_min_freq = 0
    global_max_freq = SAMPLE_FREQ/2

    # Get subject data
    cassette_data = pd.read_excel(database_path / 'SC-subjects.xls')
    cassette_data = cassette_data.rename(columns={'k': 'subject', 'sex (F=1)': 'sex', 'LightsOff': 'lights_off'})
    
    # Make sex labels readable
    cassette_data['sex'] = cassette_data['sex'].astype(str)

    cassette_data.loc[cassette_data['sex'] == '0', 'sex'] = 'M'
    cassette_data.loc[cassette_data['sex'] == '1', 'sex'] = 'F'

    # Circularize time
    time_encoder = CircularEncoder()

    cassette_data['lights_off'] = cassette_data['lights_off'].apply(lambda t: (t.hour + t.minute/60)/24)
    cassette_data['lights_off_cos'], cassette_data['lights_off_sin'] = time_encoder.transform(cassette_data['lights_off'])
    del cassette_data['lights_off']

    # Get PSG filenames
    cassette_psgs = [s for s in os.listdir(cassette_path) if 'PSG' in s]
    cassette_psgs.sort(key=lambda s: int(s[3:6]))
    cassette_data['psg_filename'] = cassette_psgs

    # Get hypnogram filenames
    cassette_hypnograms = [s for s in os.listdir(cassette_path) if 'Hypnogram' in s]
    cassette_hypnograms.sort(key=lambda s: int(s[3:6]))
    cassette_data['hypnogram_filename'] = cassette_hypnograms

    # Get technicians
    cassette_data['technician'] = [s[7] for s in cassette_data['hypnogram_filename']]

    # Begin status printing thread
    status_deque = deque(maxlen=1)
    end_var = 0

    status_thread = threading.Thread(target=print_status, args=(status_deque, 0))
    status_thread.start()

    # Add EEG signal data
    cassette_data_temp = []
    n_nights = len(cassette_data)

    for night_idx, base_row in cassette_data.iterrows():
        # Unpack and repack features
        psg_filename = base_row['psg_filename']
        hypnogram_filename = base_row['hypnogram_filename']
        base_row = base_row.tolist()
        
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

    return cassette_data
