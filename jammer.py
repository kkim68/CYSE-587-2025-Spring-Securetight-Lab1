import numpy as np
import random
import time
from typing import Optional, Dict, Tuple, List, Set
from math import cos, radians


# jamming_type should be one of:
# "CW"       # Continuous Wave
# "PULSE"    # Pulsed Noise Jamming (Burst Jamming)
# "SWEEP"    # Sweeping Jamming (Frequency Hopping Jammer)
# "DIRECTIONAL" # Directional Jamming (Beamforming Jamming)

class Jammer:
    def __init__(self,
                    jamming_type: str,
                    jamming_power_dbm: float,         # Base transmission power
                    center_freq: float = 1090e6,      # Center frequency (Hz) - defaults to ADS-B frequency

                    # CW specific parameters
                    offset_freq: float = 0.0,         # Frequency offset for CW (Hz)

                    # Pulse noise specific parameters
                    pulse_width_us: float = 1.0,            # Pulse duration
                    pulse_repetition_freq: float = 1000.0,  # Pulse frequency

                    # Sweep specific parameters
                    sweep_range_hz: float = 1e6,   # Frequency sweep range
                    sweep_time_us: float = 100.0,  # Time for one sweep

                    # Directional specific parameters
                    position: Tuple[float, float] = (0.0, 0.0),  # Jammer position
                    direction_deg: float = 0.0,                  # Beam direction
                    beam_width_deg: float = 30.0,                # Beam width
                    antenna_gain_dbi: float = 10.0):             # Antenna gain

        # Common parameters
        self.jamming_type = jamming_type
        self.jamming_power_dbm = jamming_power_dbm
        self.center_freq = center_freq
        
        # CW parameters
        self.offset_freq = offset_freq
        
        # Pulse parameters
        self.pulse_width_us = pulse_width_us
        self.pulse_repetition_freq = pulse_repetition_freq
        
        # Sweep parameters
        self.sweep_range_hz = sweep_range_hz
        self.sweep_time_us = sweep_time_us
        
        # Directional parameters
        self.position = position
        self.direction_deg = direction_deg
        self.beam_width_deg = beam_width_deg
        self.antenna_gain_dbi = antenna_gain_dbi
        
        # Internal timing
        self.start_time = time.time()

    def calculate_jamming_effect(self, bit_time_us, target_lat, target_lon, for_stat_bit_frequency_jammer):
        # Calculates jamming power at given time and target location
        # Returns jamming power in dBm

        """
            power_reduction = (freq_difference / 0.5e6) * 3
            This formula creates a simple linear relationship where:

            freq_difference is how far the jammer frequency is from 1090 MHz
            0.5e6 (500 kHz) is used as a reference bandwidth
            3 is the maximum reduction in dB

            So it works like this:

            If freq_difference = 0 Hz: (0/500kHz) * 3 = 0 dB reduction
            If freq_difference = 250kHz: (250kHz/500kHz) * 3 = 1.5 dB reduction
            If freq_difference = 500kHz: (500kHz/500kHz) * 3 = 3 dB reduction

            This assumes power reduction increases linearly with frequency difference...
            Every 167kHz difference causes 1dB reduction (500kHz/3dB)
            Maximum reduction is capped at 3dB at 500kHz offset

            This is oversimplified because real Radio Frequency filters don't have this linear response.
        """

        # bit_time_us is required for PULSE type jammer..(maybe?)
        # target_lat, target_lon is required for DIRECTIONAL type jammer.
        
        if self.jamming_type == "CW":
            # Constant power at offset frequency.
            # We don't need bit_time_us for CW.. since it just steadily sends a signal.

            freq_difference = abs(self.center_freq + self.offset_freq - 1090e6)
            for_stat_bit_frequency_jammer.append((bit_time_us, self.center_freq + self.offset_freq))

            if freq_difference < 0.5e6:  # Within 500kHz bandwidth
                power_reduction = (freq_difference / 0.5e6) * 3
                return self.jamming_power_dbm - power_reduction - + random.uniform(-0.1, 0.1)


                
        if self.jamming_type == "PULSE":
            # Note: Be sure to set pulse_width_us larger than preamble(8us) period for this to work!!
            #       So, in reality GCS will not be able to receive the message if the jammer corrupts preamble signal.
            #       And targetting preamble signal only is more practical because it is only 8 micro seconds of noise,
            #       which will be easier to deceive anomaly detection.
            #       I couldn't really modify the simulator to the level where it actually transceives the "Signal".
            #       However, the timing for preamble signal was implemented.
            #       This is why we have to set pulse_width_us variable larger than 8 in order for it to work.

            pulse_period = 1e6 / self.pulse_repetition_freq
            time_in_period = bit_time_us % pulse_period
            if time_in_period < self.pulse_width_us:
                for_stat_bit_frequency_jammer.append((bit_time_us, self.center_freq))
                return self.jamming_power_dbm + random.uniform(-2, 2)
            else:
                for_stat_bit_frequency_jammer.append((bit_time_us, float('-inf')))
            
                
        if self.jamming_type == "SWEEP":
            # Implement sweeping frequency jamming
            # Simulates frequency of the signal changes overtime

            elapsed_time = (time.time() - self.start_time) * 1e6  # Convert to microseconds
            sweep_position = (elapsed_time % self.sweep_time_us) / self.sweep_time_us
            current_freq = self.center_freq - (self.sweep_range_hz / 2) + (sweep_position * self.sweep_range_hz)

            freq_difference = abs(current_freq - 1090e6)
            for_stat_bit_frequency_jammer.append((bit_time_us, current_freq))

            if freq_difference < 0.5e6:  # Within 500kHz bandwidth
                power_reduction = (freq_difference / 0.5e6) * 3
                return self.jamming_power_dbm - power_reduction + random.uniform(-1, 1)


        
        if self.jamming_type == "DIRECTIONAL":
            # TODO: implement directional jamming
            pass
            
        return float('-inf')
