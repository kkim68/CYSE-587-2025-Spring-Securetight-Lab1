import random
import numpy as np
import time

class Spoofer:
    """
    This class simulates ADS-B spoofing by modifying legitimate drone messages
    or injecting entirely fake drones into the system.
    """
    def __init__(self, spoof_probability=0.3, fake_drone_id="FAKE123"):
        self.spoof_probability = spoof_probability
        self.fake_drone_id = fake_drone_id
        self.delta = {
            'latitude': 0,
            'longitude': 0,
            'altitude': 0
        }
        self.spoof_acceleration = {
            'latitude': 0.3,
            'longitude': 0.3,
            'altitude': 0.8
        }

        self.calculated_direction_vector = None
        self.prev_message = None
        self.count = 0

    def spoof_message(self, message):
        """Modify a real drone message or inject a fake drone."""
        if random.random() < self.spoof_probability:

            spoofed_message = message.copy()

            # spoofed_message['latitude'] += random.uniform(-0.001, 0.001)
            # spoofed_message['longitude'] += random.uniform(-0.001, 0.001)
            # spoofed_message['altitude'] += random.uniform(-5, 5)
            # spoofed_message['drone_id'] = self.fake_drone_id if random.random() < 0.5 else message['drone_id']
            # return spoofed_message, True

            print("[Spoofer] Spoofing message:", message)
            spoofed_message = self.calculate_gradual_spoof(message)
            spoofed_message['drone_id'] = message['drone_id']
            print("[Spoofer] Spoofed message:", spoofed_message)
            # spoofed_message['drone_id'] = self.fake_drone_id if random.random() < 0.5 else message['drone_id']
            return spoofed_message, True

        return message, False

    def calculate_gradual_spoof(self, message):
        spoofed_message = message.copy()

        if self.count == 0:
            self.count += 1
            self.prev_message = spoofed_message
            return spoofed_message
        else:
            if self.count == 1:
                diff_lat  = message['latitude'] - self.prev_message['latitude']
                diff_long = message['longitude'] - self.prev_message['longitude']
                diff_alt  = message['altitude'] - self.prev_message['altitude'] 
                diff_dist = (diff_lat**2 + diff_long**2 + diff_alt**2) ** (1/3)

                self.calculated_direction_vector = {
                    'latitude': diff_lat / diff_dist,
                    'longitude': diff_long / diff_dist,
                    'altitude': diff_alt / diff_dist
                }

            self.delta = {
                'latitude': self.delta['latitude'] + self.spoof_acceleration['latitude'] * self.calculated_direction_vector['latitude'],
                'longitude': self.delta['longitude'] + self.spoof_acceleration['longitude']  * self.calculated_direction_vector['longitude'],
                'altitude': self.delta['altitude'] + self.spoof_acceleration['altitude']  * self.calculated_direction_vector['altitude']
            }

            spoofed_message = {
                'latitude': message['latitude'] + self.delta['latitude'],
                'longitude': message['longitude'] + self.delta['longitude'],
                'altitude': message['altitude'] + self.delta['altitude']
            }

            if spoofed_message['altitude'] < 0:
                spoofed_message['altitude'] = 1.0

            self.count += 1
            return spoofed_message


    def spoof_signal_power(self, rx_power_dbm, noise_power_dbm, noise_figure_db):
        # Calculate appropriate spoofing signal power to maintain SNR above 0 dB.
        
    
        # Target SNR after spoofing (we chose value that is around normal)
        target_snr = 17.5  # dB        

        # Calculate maximum interference power that keeps SNR above target
        # Derived from : snr_db = rx_power_dbm - (effective_noise_power_dbm + self.noise_figure_db)
        max_interference_power = rx_power_dbm - target_snr - noise_figure_db
        
        # Set spoofing power to be slightly below this maximum
        spoofing_power = max_interference_power - 1.0

        # print(f'[!!!! SPOOFING POWER !!!!] : {spoofing_power}')
        return spoofing_power
