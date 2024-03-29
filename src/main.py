import numpy as np
from scipy.stats import truncnorm
from station import Station
from bus import Bus
from passenger import Passenger
import time

# 720 minute = 12 hrs.
MAX_TIME_MINUTES = 720

# Max number of passenger to simulate
MAX_PASSENGERS_IN_SIMULATION = 10000

# Number of stations in simulation
MAX_STATIONS = 5

# Max bus size
MAX_BUS_SIZE = 50

# Bus arrival interval. Mod this to current time, if 0 -> arrive bus at s1
# Intervals to test 5, 10, 15, 20, etc...
BUS_INTERVAL = 20

def main(bus_interval_override):
    start_time = time.time()
    if bus_interval_override > 0:
        BUS_INTERVAL = bus_interval_override

    '''
    Setup process.
    - Initializes stations
    - Generates random passengers (standard distribution)
    - Assign passengers to station (uniform distribution)
    '''

    # Static stations that will not change throughout the simulation
    s1 = Station('s1')
    s2 = Station('s2')
    s3 = Station('s3')
    s4 = Station('s4')
    s5 = Station('s5')

    stations = [s1, s2, s3, s4, s5]

    mean, sd, low, high = 360, 360, 0, 720
    passenger_randomizer = truncnorm((low-mean)/sd, (high-mean)/sd, loc=mean, scale=sd)
    random_passengers_arrival = passenger_randomizer.rvs(MAX_PASSENGERS_IN_SIMULATION)

    # Important!! Retroactively sort so we will only have to dequeue passengers that have been waiting up until a
    # specific point in time of our simulation
    random_passengers_arrival.sort()

    # print(random_passengers_arrival)

    uniform_random_station = np.random.uniform(1, MAX_STATIONS+1, MAX_PASSENGERS_IN_SIMULATION)
    # print(uniform_random_station)

    # For ever ith standard distributed passenger, assign a uniform random distributed station
    for i in range(len(random_passengers_arrival)):
        pas_arrival_time = int(random_passengers_arrival[i])
        pas_station_assignment = 's' + str(int(uniform_random_station[i]))

        # print("Queuing passenger to: " + pas_station_assignment + " | arrived at: " + str(pas_arrival_time))

        if pas_station_assignment == 's1':
            s1.queue_passenger(Passenger('s1', 'nullDestination', pas_arrival_time))
        elif pas_station_assignment == 's2':
            s2.queue_passenger(Passenger('s2', 'nullDestination', pas_arrival_time))
        elif pas_station_assignment == 's3':
            s3.queue_passenger(Passenger('s3', 'nullDestination', pas_arrival_time))
        elif pas_station_assignment == 's4':
            s4.queue_passenger(Passenger('s4', 'nullDestination', pas_arrival_time))
        elif pas_station_assignment == 's5':
            s5.queue_passenger(Passenger('s5', 'nullDestination', pas_arrival_time))

    # Keeping track of passenger count for analytics
    total_passenger_serviced_count = 0
    total_passenger_left_count = 0

    current_time = 0
    buses_in_system = []
    # Retroactively generate all bus that are meant to arrive in the system, with their arrival times
    # Arrival time from 5 min to last bus at 715
    for t in range(5, MAX_TIME_MINUTES - 4):
        if t % BUS_INTERVAL == 0:
            buses_in_system.append(Bus(t))

    # Passengers that have left the system count (waited too long)
    passenger_left_queue = []

    # Buses that have left the system
    buses_out_of_system = []

    # While time is less than simulation time OR there are buses left in the system
    while(current_time < MAX_TIME_MINUTES or len(buses_in_system) > 0):
        # We will tick in intervals of 1 min (most granularity), in some ticks we will not do anything.
        # 1) Starting at 0, we will update the clock
        current_time += 1

        # 2) Move buses:
        # 2.1) Check if any bus has left the system, if so add it to the out of system list, and then remove
        # from in system list.
        for bus in buses_in_system:
            if bus.has_left_system(current_time):
                buses_out_of_system.append(bus)
                buses_in_system.remove(bus)


        # 3) Load passengers
        for bus in buses_in_system:
            # Check if bus is at specific station
            for s in stations:
                if bus.is_at_station(s.station_id(), current_time):
                    passengers_at_station = s.get_passengers()
                    arrived_passengers = list(filter(lambda p: p.has_arrived(current_time)
                                                               and not p.has_waited_more_than_20_min(current_time),
                                                     passengers_at_station))
                    left_passengers = list(filter(lambda p: p.has_waited_more_than_20_min(current_time),
                                                  passengers_at_station))
                    have_not_arrived_passengers = list(filter(lambda p: p.has_not_arrived(current_time),
                                                              passengers_at_station))

                    # 3.1) Determine passengers that waited too long and left (add to loss revenue)
                    # Add passengers that waited too long to the left queue
                    passenger_left_queue = passenger_left_queue + left_passengers

                    # 3.2) Determine passengers to load (arrival time is < current time, and there is a bus,
                    # and there is room on bus)
                    while bus.has_room_on_bus() and len(arrived_passengers) > 0:
                        # 3.3) For all passengers to be loaded, tag wait time (current time - arrival time)
                        p = arrived_passengers[0]
                        p.set_wait_time(current_time)
                        bus.board_passenger(p)
                        total_passenger_serviced_count += 1
                        del arrived_passengers[0]

                    # 3.4) Do the actual dequeue from station and queue to bus
                    # Set the station's passengers back to the yet to arrive passengers
                    # and any arrived passengers that did not board
                    s.set_passengers(have_not_arrived_passengers + arrived_passengers)
                    # print("\n")
                    # print(bus)
                    # print("Passengers onboard: " + str(bus.passenger_count()))
                    # bus.print_queue()


    # 4) Log analytics (buses_in_system should be 0 here!!)
    # 4.1) Tally passengers still left in system (loop through all stations)
    #      They can be added to the passenger_left_queue
    for s in stations:
        passenger_left_queue = passenger_left_queue + s.get_passengers()
    total_passenger_left_count = len(passenger_left_queue)

    # 4.2) Log all passengers for analytics (services/left)
    # Log wait time
    # Log total passenger serviced count
    # Log total wait time
    # Program execution time

    revenue_gained = 3 * total_passenger_serviced_count
    revenue_loss = 3 * total_passenger_left_count

    total_serviced_passenger_wait_time = 0
    for bus in buses_out_of_system:
        serviced_passengers = bus.get_passengers()
        for passenger in serviced_passengers:
            total_serviced_passenger_wait_time += passenger.get_wait_time()

    execution_time = time.time() - start_time

    avg_wait_time = round((total_serviced_passenger_wait_time/total_passenger_serviced_count), 2)

    # Pretty print analytics
    # print("\n\n======= ANALYTICS =======")
    # print("Bus interval: " + str(BUS_INTERVAL))
    # print("Total buses passed through system: " + str(len(buses_out_of_system)))
    # print("Total passengers serviced: " + str(total_passenger_serviced_count))
    # print("Revenue gained: " + str(revenue_gained))
    # print("Revenue lost: " + str(revenue_loss))
    # print("Total wait time of all passengers: " + str(total_serviced_passenger_wait_time))
    # print("Average wait time (total wait time / # of passengers): " + str(avg_wait_time))
    # print("Program execution time (seconds): " + str(execution_time))
    # print("======= ANALYTICS =======\n\n")

    # CSV Format print
    print('{},{},{},{},{},{},{},{},{}'
          .format(BUS_INTERVAL,
                  len(buses_out_of_system),total_passenger_serviced_count,
                  total_passenger_left_count,
          revenue_gained,
          revenue_loss,
          total_serviced_passenger_wait_time,
          avg_wait_time,
          execution_time))



bus_intervals_for_simulation = [20,15,10,5]
# CSV Format print
print("interval,number_of_buses,total_passengers_serviced,total_passengers_lost,revenue_gained,"
      "revenue_lost,total_wait_time,avg_wait_time,prgm_exec_time")
for interval in bus_intervals_for_simulation:
    for run in range(1,6):
        main(interval)
