import time
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation
from drone import Drone
from route import RouteGenerator
from gcs import GCS
from adsbchannel import ADSBChannel
from adsbmessage import ADSBMessage
import pyModeS as pms

from jammer import Jammer
from spoofer import Spoofer
from util import *


# Define central location (e.g., Washington, D.C.)
# center_lat, center_lon = 38.8977, -77.0365  # White House location

center_lat, center_lon = 38.8310746001285, -77.3076380077037 # GMU Horizon Hall

# Initialize GCS
gcs = GCS(center_lat, center_lon)
gcs_pos = (center_lat, center_lon)

# Create a RouteGenerator instance
# route_gen = RouteGenerator(center_lat, center_lon, num_routes=1, waypoints_per_route=5, max_offset=0.02)
# routes = route_gen.generate_routes()

routes = [[(38.847509000825845, -77.30614845408233, 1400), (38.83763533303954, -77.30691307604847, 1220)]]
drones_icao24 = ['AAAA00', 'AAAA01', 'AAAA02', 'AAAA03', 'AAAA04', 'AAAA05', 'AAAA06', 'AAAA07', 'AAAA08', 'AAAA09', 'AAAA0A', 'AAAA0B', 'AAAA0C', 'AAAA0D', 'AAAA0E', 'AAAA0F']
# Initialize multiple drones with generated routes
drones = [
    Drone(
        id=f"{drones_icao24[i]}",
        drone_type=f"type{i}",
        acceleration_rate=2.0,
        climb_rate=3.0,
        speed=10.0 + i * 5,
        position_error=2.0,
        altitude_error=1.0,
        battery_consume_rate=0.05,
        battery_capacity=20.0 + i * 5,
        route=routes[i]
    )
    for i in range(len(routes))
]

# Initialize the communication channel, jammer, and spoofer
channel = ADSBChannel()
# jammer = Jammer(jamming_probability=0.4, noise_intensity=0.8)  # Adjust probability as needed
spoofer = Spoofer(spoof_probability=0.7, fake_drone_id="FAKE-DRONE")
jammer = None
# spoofer = None

# Create a figure for 3D plotting
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot waypoints
colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']
for i, route in enumerate(routes):
    latitudes = [p[0] for p in route]
    longitudes = [p[1] for p in route]
    altitudes = [p[2] for p in route]
    ax.scatter(latitudes, longitudes, altitudes, color=colors[i % len(colors)], label=f"Route {i+1} Waypoints")

# Plot GCS position
gcs_marker, = ax.plot([gcs.position[0]], [gcs.position[1]], [gcs.position[2]], 'ks', markersize=8, label="GCS")

# Initialize drone markers
drone_markers = {}
for i, drone in enumerate(drones):
    marker, = ax.plot([], [], [], 'o', color=colors[i % len(colors)], markersize=6, label=f"Drone {drone.id}")
    drone_markers[drone.id] = marker

ax.set_xlabel("Latitude")
ax.set_ylabel("Longitude")
ax.set_zlabel("Altitude (m)")
ax.legend()

def update(frame):
    active_drones = False
    for drone in drones:
        status = drone.calculate_navigation(1)

        if status == -2:
            print(f"Drone {drone.id} battery depleted.")
        elif status == 0:
            print(f"Drone {drone.id} completed its route.")
        else:
            active_drones = True
            # Original (ideal) message

            
            original_message = ADSBMessage(drone.id, drone.current_position[2], drone.current_position[0], drone.current_position[1])
            
            original_message_for_print = {
                'drone_id': drone.id,
                'latitude': drone.current_position[0],
                'longitude': drone.current_position[1],
                'altitude': drone.current_position[2],
                'timestamp': time.time()
            }
            

            # Step 1: Calculate basic signal parameters
            distance = ADSBChannel._haversine_distance(drone.current_position[0], drone.current_position[1], gcs_pos[0], gcs_pos[1])

            # Step 2: Simulate transmission from the drone to the GCS
            received_df17_even, received_df17_odd, delay_ns, corrupted, snr_db = channel.transmit(
                distance, original_message, jammer=jammer, spoofer=spoofer
            )

            if received_df17_even is None or received_df17_odd is None:
                print(f"Drone {drone.id} message lost during transmission.")
                continue

            # Step 3: Decode DF17 message at GCS
            latitude, longitude = pms.adsb.position(received_df17_even, received_df17_odd, time.time(), time.time()+1)
            altitude = pms.adsb.altitude(received_df17_even)


            received_message = {
                'drone_id': pms.adsb.icao(received_df17_even),
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude
            } 

            # Display Results
            print(f"Original Message: {original_message_for_print}")
            print(f"Received Message (after channel effects): {received_message}")
            print(f"Transmission Delay: {delay_ns:.2f} ns")
            print(f"SNR: {snr_db:.2f} dB")
            print(f"Message Corrupted: {'Yes' if corrupted else 'No'}")

            # Step 2: Update GCS with the received message
            gcs.receive_update(
                received_message['drone_id'],
                (
                    received_message['latitude'],
                    received_message['longitude'],
                    received_message['altitude']
                )
            )

            # Step 3: Update drone marker position
            marker = drone_markers[drone.id]
            marker.set_data([received_message['latitude']], [received_message['longitude']])
            marker.set_3d_properties([received_message['altitude']])

    if not active_drones:
        print("All drones have completed their routes or are inactive.")
        plt.close(fig)  # Close the plot window to end the simulation

    return list(drone_markers.values())

# Set up animation
ani = FuncAnimation(fig, update, frames=range(100), interval=100, blit=False)

plt.show()
