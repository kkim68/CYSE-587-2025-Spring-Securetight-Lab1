import numpy as np
import random
import time

from adsbmessage import ADSBMessage
import pyModeS as pms

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


    def corrupt_bit(self, msg: str, bit_index: int):
        byte_array = bytearray.fromhex(msg)

        # Corrupt a specific bit in the message
        # This is for jamming effect...
        byte_index = bit_index // 8
        bit_offset = 7 - (bit_index % 8)             # Flipping the MSB first..
        byte_array[byte_index] ^= (1 << bit_offset)  # Flip the bit!

        hex_string = byte_array.hex()
        return hex_string


    def transmit(self, distance, original_message, tx_power_dbm=50, bandwidth_hz=1e6, jammer=None, spoofer=None):
        # Simulate ADS-B transmission with bit-level corruption
        
        # Returns:
        # - df17_even_msg : Received even message (potentially corrupted)
        # - df17_odd_msg  : Received odd message (potentially corrupted)
        # - delay_ns: Propagation delay
        # - corrupted: Message has been corrupted or not
        # - snr_db: Signal-to-noise ratio
        # - for_stat_spoofed, for_stat_jammed: These are for n_scen_stat.py; flags for if signal was spoofed/jammed

        delay_seconds = distance / self.light_speed
        delay_ns = np.round(delay_seconds * 1e9, decimals=2)

        # Simulate propagation delay
        time.sleep(delay_seconds)
        
        path_loss_db = self.free_space_path_loss(distance)
        rx_power_dbm = tx_power_dbm - path_loss_db
        noise_power_dbm = self.thermal_noise_power(bandwidth_hz)

        # Encode the message into df17 format
        result_df17_even, result_df17_odd = original_message.encode()
        snr_db = rx_power_dbm - (noise_power_dbm + self.noise_figure_db)

        jamming_signal_power_dbm = 0
        effective_spoofing_signal_power_dbm = 0

        for_stat_jammed = False
        for_stat_spoofed = False
        
        # Apply spoofing effects if a spoofer is present
        if spoofer:
            spoofed_df17_even, spoofed_df17_odd, spoofed = spoofer.spoof_message(result_df17_even, result_df17_odd)
            if spoofed:
                # Assuming the spoofed message interferes with the legitimate signal
                spoofing_signal_power_dbm = spoofer.spoof_signal_power(snr_db) # Current SNR
                effective_spoofing_signal_power_dbm = 10 * np.log10(10**(noise_power_dbm / 10) + 10**(spoofing_signal_power_dbm / 10))
                result_df17_even = spoofed_df17_even
                result_df17_odd  = spoofed_df17_odd
                #time.sleep(1e-4)
                for_stat_spoofed = True

        # Apply jamming effects if a spoofer is present
        if jammer:
            # Simulate bit-by-bit transmission (for realistic jamming experience...)
            for bit_index in range(original_message.TOTAL_BITS):
                bit_start_us, _ = original_message.get_bit_timing(bit_index)
                
                # Calculate jamming effect for this bit
                jamming_power = jammer.calculate_jamming_effect(
                    bit_start_us,
                    original_message.latitude,
                    original_message.longitude
                )
                
                if jamming_power > float('-inf'):
                     # Calculate bit-level SNR
                    jamming_signal_power_dbm = 10 * np.log10(10**(noise_power_dbm / 10) + 10**(jamming_power / 10))
                    bit_snr_db = snr_db - jamming_signal_power_dbm

                    # Probability of bit error based on SNR
                    # The stronger the jammer signal power is, the more likely to flip a bit
                    bit_error_prob = 0.5 * np.exp(-bit_snr_db / 10)

                    # Apply bit corruption based on probability
                    if random.random() < bit_error_prob:
                        result_df17_even = self.corrupt_bit(result_df17_even, bit_index)
                        result_df17_odd = self.corrupt_bit(result_df17_odd, bit_index)        
                        for_stat_jammed = True

        # Calculate overall SNR
        snr_db -= jamming_signal_power_dbm
        snr_db -= effective_spoofing_signal_power_dbm

        # Since we are now using the bit-by-bit transmission and have ability to corrupt some bits within the message,
        # corruption will be simulated that way, rather than just compensating random value to the position.
        # So, We will now use parity bit to check if message is corrupted :)
        crc_result_even = pms.crc(result_df17_even, True)
        crc_result_odd = pms.crc(result_df17_odd, True)
        parity_even = int(result_df17_even[22:], 16) # extract 11th ~ 13th bytes
        parity_odd = int(result_df17_odd[22:], 16) 

        # print(parity_even, crc_result_even)

        corrupted = False

        if crc_result_even != parity_even or crc_result_odd != parity_odd:
            corrupted = True
        
        if snr_db < 0 or random.random() < self.error_rate:
            corrupted = True  

        return result_df17_even, result_df17_odd, delay_ns, corrupted, snr_db, for_stat_spoofed, for_stat_jammed


    # def corrupt_message(self, message):
    #     corrupted_message = message.copy()
    #     corrupted_message['latitude'] += random.uniform(-0.01, 0.01)
    #     corrupted_message['longitude'] += random.uniform(-0.01, 0.01)
    #     corrupted_message['altitude'] += random.uniform(-10, 10)
    #     return corrupted_message

