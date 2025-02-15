import numpy as np
import random
import time
from adsbmessage import ADSBMessage

class ADSBChannel:
    def __init__(self, error_rate=0.01, frequency=1090e6, noise_figure_db=5.0):
        self.error_rate = np.float64(error_rate)
        self.frequency = np.float64(frequency)
        self.noise_figure_db = np.float64(noise_figure_db)
        self.light_speed = np.float64(3e8)  # Speed of light in m/s

    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2):
        R = np.float64(6371000)  # Earth radius in meters
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        delta_phi = np.radians(lat2 - lat1)
        delta_lambda = np.radians(lon2 - lon1)

        a = (np.sin(delta_phi / 2) ** 2) + np.cos(phi1) * np.cos(phi2) * (np.sin(delta_lambda / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return R * c  # Distance in meters

    def free_space_path_loss(self, distance):
        if distance <= 0:
            return 0  # Avoid infinite loss
        wavelength = self.light_speed / self.frequency
        path_loss_db = 20 * np.log10(4 * np.pi * distance / wavelength)
        return path_loss_db

    def thermal_noise_power(self, bandwidth_hz):
        k = np.float64(1.38e-23)  # Boltzmann constant in J/K
        T = np.float64(290)  # Standard temperature in Kelvin
        noise_power_watts = k * T * bandwidth_hz
        noise_power_dbm = 10 * np.log10(noise_power_watts) + 30
        return noise_power_dbm


    def corrupt_bit(self, msg: bytearray, bit_index: int):
        """Corrupt a specific bit in the message"""
        byte_index = bit_index // 8
        bit_offset = 7 - (bit_index % 8)  # MSB first
        msg[byte_index] ^= (1 << bit_offset)  # Flip the bit


    def transmit(self, distance, original_message, tx_power_dbm=50, bandwidth_hz=1e6, jammer=None, spoofer=None):
        """
        Simulate ADS-B transmission with bit-level corruption
        
        Returns:
        - df17_even_msg : Received even message (potentially corrupted)
        - df17_odd_msg  : Received odd message (potentially corrupted)
        - delay_ns: Propagation delay
        - snr_db: Signal-to-noise ratio
        - corrupted_bits: Set of corrupted bit indices
        """

        delay_seconds = distance / self.light_speed
        delay_ns = np.round(delay_seconds * 1e9, decimals=2)

        # Simulate propagation delay
        time.sleep(delay_seconds)
        
        path_loss_db = self.free_space_path_loss(distance)
        rx_power_dbm = tx_power_dbm - path_loss_db
        noise_power_dbm = self.thermal_noise_power(bandwidth_hz)

        # Encode the message into df17 format
        result_df17_even, result_df17_odd = original_message.encode()
        corrupted_bits = set()
        
        snr_db = rx_power_dbm - (noise_power_dbm + self.noise_figure_db)

        jamming_signal_power_dbm = 0
        effective_spoofing_signal_power_dbm = 0

        # Apply jamming effects if a spoofer is present
        if jammer:
            # Simulate bit-by-bit transmission (for realistic jamming experience...)
            for bit_index in range(original_message.TOTAL_BITS):
                bit_start_us, bit_end_us = original_message.get_bit_timing(bit_index)
                
                # Calculate jamming effect for this bit
                jamming_power, affected_bits = jammer.calculate_jamming_effect(encoded_msg, bit_start_us)
                
                if jamming_power > float('-inf'):
                    # Calculate bit-level SNR
                    jamming_signal_power_dbm = 10 * np.log10(10**(noise_power_dbm / 10) + 10**(jamming_power / 10))
                    bit_snr_db = rx_power_dbm - (jamming_signal_power_dbm + self.noise_figure_db)
                    
                    # Probability of bit error based on SNR
                    bit_error_prob = 0.5 * np.exp(-bit_snr_db / 10)
                    
                    # Apply bit corruption based on probability
                    if random.random() < bit_error_prob:
                        self.corrupt_bit(encoded_msg, bit_index)
                        corrupted_bits.add(bit_index)


        # Apply spoofing effects if a spoofer is present
        if spoofer:
            spoofed_df17_even, spoofed_df17_odd, spoofed = spoofer.spoof_message(result_df17_even, result_df17_odd)
            if spoofed:
                # Assuming the spoofed message interferes with the legitimate signal
                spoofing_signal_power_dbm = spoofer.spoof_signal_power(rx_power_dbm, noise_power_dbm, self.noise_figure_db)
                effective_spoofing_signal_power_dbm = 10 * np.log10(10**(noise_power_dbm / 10) + 10**(spoofing_signal_power_dbm / 10))
                result_df17_even = spoofed_df17_even
                result_df17_odd  = spoofed_df17_odd

        # Calculate overall SNR
        snr_db = snr_db - jamming_signal_power_dbm
        snr_db = snr_db - effective_spoofing_signal_power_dbm
        

        # Since we are now using the bit-by-bit transmission and have ability to corrupt some bits within the message,
        # corruption will be simulated that way, rather than just compensating random value to the position.
        # So, We will now use parity bit to check if message is corrupted :)
        # TODO: check corrupted using CRC
        corrupted = False

        return result_df17_even, result_df17_odd, delay_ns, corrupted, snr_db


    def corrupt_message(self, message):
        corrupted_message = message.copy()
        corrupted_message['latitude'] += random.uniform(-0.01, 0.01)
        corrupted_message['longitude'] += random.uniform(-0.01, 0.01)
        corrupted_message['altitude'] += random.uniform(-10, 10)
        return corrupted_message
