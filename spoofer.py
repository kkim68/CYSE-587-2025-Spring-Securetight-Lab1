import random
import numpy as np
import time
import pyModeS as pms
from adsbmessage import ADSBMessage
from util import *

class Spoofer:
    """
    This class simulates ADS-B spoofing by modifying legitimate drone messages
    or injecting entirely fake drones into the system.
    """

    def __init__(self, spoof_probability=0.3, fake_drone_id="FAKE123"):
        self.spoof_probability = spoof_probability
        self.fake_drone_id = fake_drone_id

        self.delta = {'latitude': 0, 'longitude': 0, 'altitude': 0}

        # Gradual acceleration starts small and increases over time
        self.spoof_acceleration = {'latitude': 0.0001, 'longitude': 0.0001, 'altitude': 3}
        
        # Introduce a decay factor to prevent sudden jumps
        self.spoof_decay_factor = 0.98  # Gradually slow down spoofing
        
        self.calculated_direction_vector = None
        self.prev_message = None
        self.count = 0

    def spoof_message(self, df17_even, df17_odd):        
        latitude, longitude = pms.adsb.position(df17_even, df17_odd, time.time(), time.time()+1)
        altitude = pms.adsb.altitude(df17_even)
        # print(latitude, longitude, altitude)

        message = {
            'drone_id': pms.adsb.icao(df17_even),
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude
        } 

        """Modify a real drone message or inject a fake drone."""
        if random.random() < self.spoof_probability:
            print("[Spoofer] Spoofing message:", message)
            spoofed_message = self.calculate_gradual_spoof(message)
            spoofed_message['drone_id'] = message['drone_id']
            print("[Spoofer] Spoofed message:", spoofed_message)

            spoofed_df17_even, spoofed_df17_odd = ADSBMessage(
                spoofed_message['drone_id'], spoofed_message['altitude'], spoofed_message['latitude'], spoofed_message['longitude']
            ).encode()
            return spoofed_df17_even, spoofed_df17_odd, True

        return df17_even, df17_odd, False

    def calculate_gradual_spoof(self, message):
        spoofed_message = message.copy()

        if self.count == 0:
            self.count += 1
            self.prev_message = spoofed_message
            return spoofed_message
        else:
            if self.count == 1:
                diff_lat = message['latitude'] - self.prev_message['latitude']
                diff_long = message['longitude'] - self.prev_message['longitude']
                diff_alt = message['altitude'] - self.prev_message['altitude']
                
                diff_dist = (diff_lat**2 + diff_long**2 + diff_alt**2) ** (1/3)

                # Normalize direction vector
                self.calculated_direction_vector = {
                    'latitude': diff_lat / diff_dist,
                    'longitude': diff_long / diff_dist,
                    'altitude': diff_alt / diff_dist
                }

            # Gradual acceleration increase over time
            self.spoof_acceleration['latitude'] *= self.spoof_decay_factor
            self.spoof_acceleration['longitude'] *= self.spoof_decay_factor
            self.spoof_acceleration['altitude'] *= self.spoof_decay_factor
            
            #  Apply acceleration over time to simulate gradual drift
            self.delta = {
                'latitude': self.delta['latitude'] + (self.spoof_acceleration['latitude'] * self.calculated_direction_vector['latitude']),
                'longitude': self.delta['longitude'] + (self.spoof_acceleration['longitude'] * self.calculated_direction_vector['longitude']),
                'altitude': self.delta['altitude'] + (self.spoof_acceleration['altitude'] * self.calculated_direction_vector['altitude'])
            }


            # # Introduce slight noise to prevent perfectly linear drift (makes spoofing more realistic)
            noise_factor = 0.0001
            self.delta['latitude'] += random.uniform(-noise_factor, noise_factor)
            self.delta['longitude'] += random.uniform(-noise_factor, noise_factor)
            self.delta['altitude'] += random.uniform(-0.5, 0.5)

            # I believe above is not required anymore thanks to the nature "error" of ADS-B.
            # Each 17-bit field for latitude and longitude provides a quantization level of 2^17 = 131,072 discrete values.
            # The precision this translates to depends on the encoding zone since CPR divides the globe into zones...
            # This is about 0.001 ~ 0.002 degrees error by nature.
            # But since it is already implemented, I will leave it. 


            # Apply spoofing changes
            spoofed_message = {
                'latitude': message['latitude'] + self.delta['latitude'],
                'longitude': message['longitude'] + self.delta['longitude'],
                'altitude': message['altitude'] + self.delta['altitude']
            }

            # Prevent negative altitude
            if spoofed_message['altitude'] < 0:
                spoofed_message['altitude'] = 1.0

            self.count += 1
            return spoofed_message

    def spoof_signal_power(self, snr_db):
        # Set spoofing signal power dynamically based on SNR threshold
        target_snr = 17.5  # dB        
        max_interference_power = snr_db - target_snr
        spoofing_power = max_interference_power - 1.0
        return spoofing_power