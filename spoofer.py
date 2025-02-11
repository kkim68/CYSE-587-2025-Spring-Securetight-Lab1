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
        self.history = []

    def spoof_message(self, message):
        """Modify a real drone message or inject a fake drone."""
        if random.random() < self.spoof_probability:
            print("[Spoofer] Spoofing message:", message)
            spoofed_message = message.copy()
            delta_lat, delta_long, delta_alt = self.calculate_gradual_change(message)
            spoofed_message['latitude'] += delta_lat
            spoofed_message['longitude'] += delta_long
            spoofed_message['altitude'] += delta_alt
            spoofed_message['drone_id'] = message['drone_id']
            print("[Spoofer] Spoofed message:", spoofed_message)
            # spoofed_message['drone_id'] = self.fake_drone_id if random.random() < 0.5 else message['drone_id']

            return spoofed_message, True

        return message, False

    def calculate_gradual_change(self, message):
        # TODO: Calculate gradual change of position in terms of momentum, vector(direction), previous position...
        # TODO: maybe we should maintain "history" of the spoofed drone positions.
        
        # [!!] Guys, this is still random.
        #      Maybe we should pick a specific direction and gradually accelerate the drone into that direction.
        #      Any comments would be appreciated.

        delta_lat = random.uniform(-0.0001, 0.0001)
        delta_long = random.uniform(-0.0001, 0.0001)
        delta_alt = random.uniform(-5, 5)

        return delta_lat, delta_long, delta_alt


    def spoof_signal_power(self, rx_power_dbm, noise_power_dbm, noise_figure_db):
        # Calculate appropriate spoofing signal power to maintain SNR above 0 dB.
        
    
        # Target SNR after spoofing (slightly above 0 dB to avoid corruption)
        target_snr = 1.0  # dB        

        # Calculate maximum interference power that keeps SNR above target
        # Derived from : snr_db = rx_power_dbm - (effective_noise_power_dbm + self.noise_figure_db)
        max_interference_power = rx_power_dbm - target_snr - noise_figure_db
        
        # Set spoofing power to be slightly below this maximum
        spoofing_power = max_interference_power - 1.0

        # print(f'[!!!! SPOOFING POWER !!!!] : {spoofing_power}')
        return spoofing_power
