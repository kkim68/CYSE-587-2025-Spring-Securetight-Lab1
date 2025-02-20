# Decoder(pyModeS)  : https://github.com/junzis/pyModeS/tree/faf43134e5b024bc2003910d2dd252b5457c407e
# Encoder(ADSB-Out) : https://github.com/lyusupov/ADSB-Out/blob/master/ADSB_Encoder.py

# Reference : https://airmetar.main.jp/radio/ADS-B%20Decoding%20Guide.pdf, Slide 3
#             https://mode-s.org/1090mhz/content/ads-b/1-basics.html

"""
+----------------------------------------+-----------------------------------------------------------------------------------+--------------------------+
|   DF  | CA  |     ICAO24 ADDRESS       |                       DATA                                                        |           CRC            |
+----------------------------------------+-------+----+-------+--------------+---+---+-------------------+-------------------+--------------------------+
|       |     |                          |  TC   | SS | NICsb |     ALT      | T | F |      LAT-CPR      |      LON-CPR      |                          |
+----------------------------------------+-------+----+-------+--------------+---+---+-------------------+-------------------+--------------------------+
| 10001 | 101 | 010000000110001000011101 | 01011 | 00 |   0   | 110000111000 | 0 | 0 | 10110101101001000 | 01100100010101100 | 001010000110001110100111 |

|   1st-byte  |      2nd    |    3rd     |          4th       |                       5th~10th                               |        11th~13th         |

* TC: Type Code, SS: Surveillance Status, NICsb: Single Antenna Flag, T: Time Flag, F: CPR odd/even Flag
"""


# ADS-B message with bit-level access and timing

import pyModeS as pms
from adsb_message_encoder import *


class ADSBMessage:

	def __init__(self, icao24: str, altitude: float, latitude: float, longitude: float):
	    self.df = 17  # ADS-B message type - Downlink Format (17), 10001 in binary
	                  # However, this is not used... since the library for encoding uses DF=17.

	    self.ca = 5   # Capability - additional identifier (5), 101 in binary
	    self.tc = 11
	    self.ss = 0
	    self.nicsb = 0
	    self.time = 0 

	    self.icao24 = int(icao24, 16) # A unique 24-bit identifier for each aircraft (so-called ICAO aircraft address)
	    
	    self.altitude = altitude
	    self.latitude = latitude
	    self.longitude = longitude
	    
	    # Timing constants
	    self.PREAMBLE_DURATION_US = 8.0
	    self.BIT_DURATION_US = 1.0  # 1μs per bit
	    self.TOTAL_BITS = 112
	    


	def get_bit_timing(self, bit_index: int):
	    # Get start and end timing for a specific bit
	    # Add preamble duration to all bit timings

	    start_time = self.PREAMBLE_DURATION_US + (bit_index * self.BIT_DURATION_US)
	    end_time = start_time + self.BIT_DURATION_US
	    return start_time, end_time


	def encode(self):
	    surface = False
	    (df17_even, df17_odd) = df17_pos_rep_encode(self.ca, self.icao24, self.tc, self.ss, self.nicsb, self.altitude, self.time, self.latitude, self.longitude, surface)
	    return (df17_even, df17_odd)




	""" We are now just using pyModeS package...
	    No need for below function anymore

	@staticmethod
	def _pack_position(alt: int, lat: int, lon: int):
	    # Pack position data into 6 bytes (this will become 5-10th bytes)

	    data = bytearray(6)
	    data[0] = (alt >> 4) & 0xFF
	    data[1] = ((alt & 0xF) << 4) | ((lat >> 16) & 0xF)
	    data[2] = (lat >> 8) & 0xFF
	    data[3] = lat & 0xFF
	    data[4] = (lon >> 8) & 0xFF
	    data[5] = lon & 0xFF
	    return data


	# This method was taken from:
	# https://github.com/junzis/pyModeS/blob/e647863b249f7688940f50b097ba6d667dacb69c/src/pyModeS/py_common.py#L35

	@staticmethod
	def _calculate_crc(mbytes: bytes):
	    # the CRC generator
	    G = [int("11111111", 2), int("11111010", 2), int("00000100", 2), int("10000000", 2)]

	    for ibyte in range(len(mbytes) - 3):
	        for ibit in range(8):
	            mask = 0x80 >> ibit
	            bits = mbytes[ibyte] & mask

	            if bits > 0:
	                mbytes[ibyte] = mbytes[ibyte] ^ (G[0] >> ibit)
	                mbytes[ibyte + 1] = mbytes[ibyte + 1] ^ (
	                    0xFF & ((G[0] << 8 - ibit) | (G[1] >> ibit))
	                )
	                mbytes[ibyte + 2] = mbytes[ibyte + 2] ^ (
	                    0xFF & ((G[1] << 8 - ibit) | (G[2] >> ibit))
	                )
	                mbytes[ibyte + 3] = mbytes[ibyte + 3] ^ (
	                    0xFF & ((G[2] << 8 - ibit) | (G[3] >> ibit))
	                )

	    result = (mbytes[-3] << 16) | (mbytes[-2] << 8) | mbytes[-1]

	    return result
	"""