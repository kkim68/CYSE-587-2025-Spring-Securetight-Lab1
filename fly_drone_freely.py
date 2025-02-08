from drone import Drone, plot_drone_path

DRONE_CONFIG = [{
	'id': 1,
	'drone_type': 'type1',
	'acceleration_rate': 2,
	'climb_rate': 2.7,               # 2.7m/s (This is about 6 miles/hour)
	'speed': 8.3,                    # 8.3m/s (This is about 18 miles/hour)
	'position_error': 2,             # 2m error
	'altitude_error': 1,             # 1m error
	'battery_consume_rate': 0.00625, # Ah
	'battery_capacity': 45,          # 45,000 mAh (This gives us about 2hrs of aviation)
}]

route = [
	[38.8310746001285, -77.3076380077037, 0],     # GMU Horizon Hall
	[38.8310746001285, -77.3076380077037, 21],    # GMU Horizon Hall
	[38.83242457930523, -77.30643216075059, 22],  # GMU Sandbridge Hall
	[38.83625769788175, -77.30650707790234, 24],  # University Drive Park
	[38.8477807377734, -77.30534738657532, 23],   # Old Town Plaza Shopping Mall
	[38.8477807377734, -77.30534738657532, 0]	  # Old Town Plaza Shopping Mall
]

def main():
	drone1 = Drone(DRONE_CONFIG[0]['id'], DRONE_CONFIG[0]['drone_type'], DRONE_CONFIG[0]['acceleration_rate'], 
		DRONE_CONFIG[0]['climb_rate'], DRONE_CONFIG[0]['speed'], DRONE_CONFIG[0]['position_error'],
		DRONE_CONFIG[0]['altitude_error'], DRONE_CONFIG[0]['battery_consume_rate'], DRONE_CONFIG[0]['battery_capacity'],
		route)

	plot_drone_path(route, drone1)

main()