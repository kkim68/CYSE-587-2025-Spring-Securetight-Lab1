import time
import numpy as np
import matplotlib.pyplot as plt
import os
from drone import Drone
from route import RouteGenerator
from gcs import GCS
from adsbchannel import ADSBChannel
from adsbmessage import ADSBMessage
import pyModeS as pms

from jammer import Jammer
from spoofer import Spoofer
import seaborn as sns


# Define central location (e.g., Washington, D.C.)
center_lat, center_lon = 38.8977, -77.0365  # White House location

# Initialize GCS
gcs = GCS(center_lat, center_lon)
gcs_pos = (center_lat, center_lon)

# Create a RouteGenerator instancz
route_gen = RouteGenerator(center_lat, center_lon, num_routes=3, waypoints_per_route=5, max_offset=0.02)
routes = route_gen.generate_routes()

# Function to initialize drones
def initialize_drones():
    return [
        Drone(
            id=f"{i+1}",
            drone_type=f"type{i+1}",
            acceleration_rate=2.0,
            climb_rate=3.0,
            speed=10.0 + i*5,
            position_error=2.0,
            altitude_error=1.0,
            battery_consume_rate=0.05,
            battery_capacity=10.0 + i*5,
            route=routes[i]
        )
        for i in range(len(routes))
    ]

# Simulation scenarios
scenarios = {
    "No Attacks": {"jamming": False, "spoofing": False},
    "Only Spoofing": {"jamming": False, "spoofing": True},
    "Only Jamming": {"jamming": True, "spoofing": False},
    "Jamming and Spoofing": {"jamming": True, "spoofing": True},
    "Aggressive Spoofing": {"jamming": False, "spoofing": True, "spoof_probability": 0.7}
}


def plot_bit_sequence_jammer_power(jammer_data):
    plt.figure(figsize=(12, 6))

    for jammer in jammer_data.items():
        jammer_name = jammer[0]
        jammer_values = jammer[1]
        times, bit_power_jammer_values = zip(*jammer_values)
        plt.plot(times, bit_power_jammer_values, label=jammer_name)

    plt.xlabel('Bit Timing in message')
    plt.ylabel('Jammer Power')
    plt.title('Jammer Power Representation over bit sequence')
    plt.legend()
    plt.grid(True)
    plt.savefig('results/jammer_power.png')
    plt.show()



def plot_snr_data(results):
    """
    Plots SNR data as both line plots and box plots for each scenario.

    Parameters:
        results (dict): Dictionary containing SNR data for each scenario.
    """

    # Box Plot
    plt.figure(figsize=(12, 6))
    snr_data = []
    scenarios = []
    for scenario, data in results.items():
        if 'snr' in data and data['snr']:
            _, snr_values = zip(*data['snr'])
            snr_data.extend(snr_values)
            scenarios.extend([scenario] * len(snr_values))
    sns.boxplot(x=scenarios, y=snr_data)
    plt.xlabel('Scenario')
    plt.ylabel('SNR (dB)')
    plt.title('SNR Distribution across Different Scenarios')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.savefig('results/snr_box_plot.png')
    plt.show()

def plot_latency_data(results):
    plt.figure(figsize=(12, 6))
    for scenario, data in results.items():
        if 'latency' in data and data['latency']:
            messages, latencies = zip(*data['latency'])
            plt.plot(messages, latencies, label=scenario)
    plt.xlabel('Total Messages Sent')
    plt.ylabel('Latency (ms)')
    plt.title('Latency over Simulation Time for Different Scenarios')
    plt.legend()
    plt.grid(True)
    plt.savefig('results/latency_plot.png')
    plt.show()

def plot_throughput_data(results):
    plt.figure(figsize=(12, 6))
    for scenario, data in results.items():
        if 'throughput' in data and data['throughput']:
            times, throughputs = zip(*data['throughput'])
            plt.plot(times, throughputs, label=scenario)
    plt.xlabel('Elapsed Time (s)')
    plt.ylabel('Throughput (messages/second)')
    plt.title('Throughput over Simulation Time for Different Scenarios')
    plt.legend()
    plt.grid(True)
    plt.savefig('results/throughput_plot.png')
    plt.show()

def plot_packet_loss_data(results, colors=None, output_path='results/packet_loss.png'):
    """
    Plots packet loss over time for each scenario.

    Parameters:
        results (dict): Dictionary containing packet loss data for each scenario.
        colors (list, optional): List of colors for each scenario plot. Defaults to None.
        output_path (str, optional): File path to save the plot image. Defaults to 'results/packet_loss.png'.
    """
    if colors is None:
        colors = ['blue', 'green', 'orange', 'red', 'purple']

    plt.figure(figsize=(12, 8))

    for (scenario, data), color in zip(results.items(), colors):
        if 'packet_loss' in data and data['packet_loss']:
            times, packet_loss = zip(*data['packet_loss'])
            plt.plot(times, packet_loss, label=scenario, color=color)

    plt.xlabel('Total Messages Sent')
    plt.ylabel('Packet Loss (%)')
    plt.title('Packet Loss over Simulation Time for Different Scenarios')
    plt.legend()
    plt.grid(True)
    plt.savefig(output_path)
    plt.show()



# Function to run a simulation scenario
def run_simulation(jamming=False, spoofing=False, spoof_probability=0.3):
    channel = ADSBChannel()
    jammer = Jammer(jamming_type="PULSE",jamming_power_dbm=45, center_freq=1090e6, pulse_width_us=15.0, pulse_repetition_freq=2000.0)
    spoofer = Spoofer(spoof_probability=spoof_probability, fake_drone_id="FAKE-DRONE")

    if not jamming:
        jammer = None 
    if not spoofing:
        spoofer = None

    drones = initialize_drones()

    total_messages = 0
    lost_messages = 0
    packet_loss_over_time = []
    snr_values = []
    latency_values = []
    throughput_values = []

    start_time = time.time()

    for drone in drones:
        while True:
            status = drone.calculate_navigation(1)
            if status in [-1, -2, 0]:
                break

            send_time = time.time()

            # original_message = {
            #     'drone_id': drone.id,
            #     'latitude': drone.current_position[0],
            #     'longitude': drone.current_position[1],
            #     'altitude': drone.current_position[2],
            #     'timestamp': send_time
            # }

            distance = ADSBChannel._haversine_distance(drone.current_position[0], drone.current_position[1], gcs_pos[0], gcs_pos[1])
            original_adsb_message = ADSBMessage(drone.id, drone.current_position[2], drone.current_position[0], drone.current_position[1])

            received_df17_even, received_df17_odd, delay_ns, corrupted, snr_db, spoofed, jammed, _ = channel.transmit(
                distance, original_adsb_message, jammer=jammer, spoofer=spoofer
            )

            receive_time = time.time()
            
            total_messages += 1

            if corrupted:
                lost_messages += 1
                packet_loss_over_time.append((total_messages, lost_messages / total_messages * 100))
                snr_values.append((total_messages, snr_db))
                continue
                
            else:
                latitude, longitude = pms.adsb.position(received_df17_even, received_df17_odd, time.time(), time.time()+1)
                altitude = pms.adsb.altitude(received_df17_even)

                received_message = {
                    'drone_id': pms.adsb.icao(received_df17_even),
                    'latitude': latitude,
                    'longitude': longitude,
                    'altitude': altitude
                } 

                gcs.receive_update(
                    received_message['drone_id'],
                    (
                        received_message['latitude'],
                        received_message['longitude'],
                        received_message['altitude']
                    )
                )
                packet_loss_over_time.append((total_messages, lost_messages / total_messages * 100))
                snr_values.append((total_messages, snr_db))

                # Calculate latency in milliseconds
                latency = (receive_time - send_time) * 1000
                latency_values.append((total_messages, latency))

                # Calculate throughput (messages per second)
                elapsed_time = receive_time - start_time
                throughput = total_messages / elapsed_time
                throughput_values.append((elapsed_time, throughput))

    return packet_loss_over_time, snr_values, latency_values, throughput_values


# Function to run a simulation scenario
def run_simulation_jammer():
    jammer_data = {}

    channel = ADSBChannel()
        
    jammer_route_gen = RouteGenerator(center_lat, center_lon, num_routes=1, waypoints_per_route=2, max_offset=0.02)
    jammer_routes = jammer_route_gen.generate_routes()


    

    jammers = [
        Jammer(jamming_type="CW"   , jamming_power_dbm=45, center_freq=1090e6, offset_freq=0.2e6),
        Jammer(jamming_type="PULSE", jamming_power_dbm=35, center_freq=1090e6, pulse_width_us=15.0, pulse_repetition_freq=40000.0),
        Jammer(jamming_type="SWEEP", jamming_power_dbm=25, center_freq=1090e6, sweep_range_hz=1e6, sweep_time_us=100.0)
    ]

    for jammer in jammers:
        bit_power_jammer_data = None

        drone = Drone(
                id=f"AA0000",
                drone_type="AA0000",
                acceleration_rate=2.0,
                climb_rate=3.0,
                speed=10.0,
                position_error=2.0,
                altitude_error=1.0,
                battery_consume_rate=0.05,
                battery_capacity=10.0,
                route=jammer_routes[0]
        )

        while True:

            status = drone.calculate_navigation(1)
            if status in [-1, -2, 0]:
                break

            distance = ADSBChannel._haversine_distance(drone.current_position[0], drone.current_position[1], gcs_pos[0], gcs_pos[1])
            original_adsb_message = ADSBMessage(drone.id, drone.current_position[2], drone.current_position[0], drone.current_position[1])

            _, _, _, _, _, _, _, bit_power_jammer_data = channel.transmit(
                distance, original_adsb_message, jammer=jammer, spoofer=None
            )

        jammer_data[jammer.jamming_type] = bit_power_jammer_data

    return jammer_data


# Run simulations for each scenario and collect results

results = {}
for scenario, params in scenarios.items():
    print(f"Running scenario: {scenario}")
    packet_loss_data, snr_data, latency_data, throughput_data = run_simulation(**params)
    results[scenario] = {
        'packet_loss': packet_loss_data,
        'snr': snr_data,
        'latency': latency_data,
        'throughput': throughput_data
    }


bit_power_jammer_data = run_simulation_jammer()

# Ensure the 'results' directory exists
if not os.path.exists('results'):
    os.makedirs('results')

plot_bit_sequence_jammer_power(bit_power_jammer_data)

# Plotting packet loss over time for each scenario
plot_packet_loss_data(results)

# Plotting SNR over time for each scenario
plot_snr_data(results)

# Plotting Latency over time for each scenario
plot_latency_data(results)

# Plotting Throughput over time for each scenario
plot_throughput_data(results)


