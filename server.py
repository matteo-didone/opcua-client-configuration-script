import asyncio
import logging
from asyncua import Server, ua
from asyncua.common.methods import uamethod
import random
from datetime import datetime


class SawMillServer:
    def __init__(self):
        self.server = Server()
        self.sawmill_vars = {}
        self.logger = logging.getLogger(__name__)
        self._running = True

        # Target values for parameters (realistic industrial values)
        self.target_values = {
            "cutting_speed": 20.0,  # m/min (15-25 typical for industrial sawmills)
            "motor_speed": 1800.0,  # RPM (1500-2000 common for industrial motors)
            "power_consumption": 75.0,  # kW (60-90 typical for industrial sawmills)
            "temperature": 45.0,  # °C (40-60 normal operating temp)
            "vibration": 4.0,  # mm/s RMS (2-10 normal range)
            "pressure": 175.0,  # bar (150-200 typical hydraulic pressure)
            "pieces_count": 0
        }

    async def init(self):
        await self.server.init()

        # Setup server
        self.server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
        self.server.set_server_name("Sawmill OPC UA Server")

        # Register namespace
        uri = "http://examples.freeopcua.github.io"
        idx = await self.server.register_namespace(uri)
        self.logger.info(f"Registered namespace with index {idx}: {uri}")

        # Create base structure
        root = self.server.nodes.objects

        # Define paths
        sawmill_path = "SawMill"
        states_path = f"{sawmill_path}/States"
        params_path = f"{sawmill_path}/Parameters"
        counters_path = f"{sawmill_path}/Counters"
        alarms_path = f"{sawmill_path}/Alarms"
        sensors_path = f"{sawmill_path}/Sensors"

        # Create folder structure
        sawmill = await root.add_folder(f"ns={idx};s={sawmill_path}", "SawMill")
        states = await sawmill.add_folder(f"ns={idx};s={states_path}", "States")
        parameters = await sawmill.add_folder(f"ns={idx};s={params_path}", "Parameters")
        counters = await sawmill.add_folder(f"ns={idx};s={counters_path}", "Counters")
        alarms = await sawmill.add_folder(f"ns={idx};s={alarms_path}", "Alarms")
        sensors = await sawmill.add_folder(f"ns={idx};s={sensors_path}", "Sensors")

        # Add state variables
        self.sawmill_vars["is_active"] = await states.add_variable(
            f"ns={idx};s={states_path}/IsActive", "IsActive", False)
        self.sawmill_vars["is_working"] = await states.add_variable(
            f"ns={idx};s={states_path}/IsWorking", "IsWorking", False)
        self.sawmill_vars["is_stopped"] = await states.add_variable(
            f"ns={idx};s={states_path}/IsStopped", "IsStopped", True)

        # Add parameter variables
        self.sawmill_vars["cutting_speed"] = await parameters.add_variable(
            f"ns={idx};s={params_path}/CuttingSpeed", "CuttingSpeed", self.target_values["cutting_speed"])
        self.sawmill_vars["motor_speed"] = await parameters.add_variable(
            f"ns={idx};s={params_path}/MotorSpeed", "MotorSpeed", self.target_values["motor_speed"])
        self.sawmill_vars["power_consumption"] = await parameters.add_variable(
            f"ns={idx};s={params_path}/PowerConsumption", "PowerConsumption", self.target_values["power_consumption"])

        # Add counter variables
        self.sawmill_vars["pieces_count"] = await counters.add_variable(
            f"ns={idx};s={counters_path}/PiecesCount", "PiecesCount", self.target_values["pieces_count"])

        # Add alarm variables
        self.sawmill_vars["has_alarm"] = await alarms.add_variable(
            f"ns={idx};s={alarms_path}/HasAlarm", "HasAlarm", False)
        self.sawmill_vars["has_error"] = await alarms.add_variable(
            f"ns={idx};s={alarms_path}/HasError", "HasError", False)

        # Add sensor variables
        self.sawmill_vars["temperature"] = await sensors.add_variable(
            f"ns={idx};s={sensors_path}/Temperature", "Temperature", self.target_values["temperature"])
        self.sawmill_vars["vibration"] = await sensors.add_variable(
            f"ns={idx};s={sensors_path}/Vibration", "Vibration", self.target_values["vibration"])
        self.sawmill_vars["pressure"] = await sensors.add_variable(
            f"ns={idx};s={sensors_path}/Pressure", "Pressure", self.target_values["pressure"])
        self.sawmill_vars["speed"] = await sensors.add_variable(
            f"ns={idx};s={sensors_path}/Speed", "Speed", self.target_values["motor_speed"])

        # Make variables writable
        for var in self.sawmill_vars.values():
            await var.set_writable()

        # Log created variables
        for name, var in self.sawmill_vars.items():
            node_id = var.nodeid.to_string()
            self.logger.info(f"Created variable {name} with node ID: {node_id}")

    async def start(self):
        """Start the server and run the simulation"""
        self._running = True
        self.logger.info("Starting server...")

        async with self.server:
            while self._running:
                await self.update_simulation()
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the server gracefully"""
        self._running = False
        self.logger.info("Stopping server...")

    async def update_simulation(self):
        """Update simulation values with realistic changes"""
        try:
            # Read current states
            is_active = await self.sawmill_vars["is_active"].read_value()
            is_working = await self.sawmill_vars["is_working"].read_value()

            # Every 10 seconds toggle active state to simulate machine cycles
            current_time = datetime.now()
            if current_time.second % 10 == 0:
                new_active = not is_active
                new_working = not is_working
                await self.sawmill_vars["is_active"].write_value(new_active)
                await self.sawmill_vars["is_working"].write_value(new_working)
                await self.sawmill_vars["is_stopped"].write_value(not new_active)
                self.logger.info(f"Toggled machine state - Active: {new_active}, Working: {new_working}")

            if is_active:
                # Update cutting speed (15-25 m/min)
                current_speed = await self.sawmill_vars["cutting_speed"].read_value()
                new_speed = self.target_values["cutting_speed"] + random.uniform(-2, 2)
                new_speed = max(15, min(25, new_speed))
                await self.sawmill_vars["cutting_speed"].write_value(new_speed)

                # Update motor speed (±5% variation)
                motor_speed = self.target_values["motor_speed"] + random.uniform(-90, 90)
                await self.sawmill_vars["motor_speed"].write_value(motor_speed)
                await self.sawmill_vars["speed"].write_value(motor_speed)  # Update speed sensor

                # Update power consumption (varies with cutting speed)
                power_base = self.target_values["power_consumption"]
                power = power_base + (new_speed - 20) * 2  # 2kW per m/min deviation
                power += random.uniform(-1, 1)  # Small random variation
                power = max(60, min(90, power))  # Limit to realistic range
                await self.sawmill_vars["power_consumption"].write_value(power)

                # Update temperature (40-60°C, slow changes)
                current_temp = await self.sawmill_vars["temperature"].read_value()
                new_temp = current_temp + random.uniform(-0.2, 0.3)
                new_temp = max(40, min(60, new_temp))
                await self.sawmill_vars["temperature"].write_value(new_temp)

                # Update vibration (2-10 mm/s RMS)
                current_vib = await self.sawmill_vars["vibration"].read_value()
                new_vib = current_vib + random.uniform(-0.3, 0.3)
                new_vib = max(2, min(10, new_vib))
                await self.sawmill_vars["vibration"].write_value(new_vib)

                # Update hydraulic pressure (150-200 bar)
                current_pressure = await self.sawmill_vars["pressure"].read_value()
                new_pressure = current_pressure + random.uniform(-2, 2)
                new_pressure = max(150, min(200, new_pressure))
                await self.sawmill_vars["pressure"].write_value(new_pressure)

                if is_working:
                    # Increment piece count (20% chance per second when working)
                    if random.random() < 0.2:
                        pieces = await self.sawmill_vars["pieces_count"].read_value()
                        await self.sawmill_vars["pieces_count"].write_value(pieces + 1)

                    # Handle alarms and errors
                    if power > 85:  # High power consumption alarm
                        await self.sawmill_vars["has_alarm"].write_value(True)
                        self.logger.warning(f"High power consumption alarm triggered: {power:.1f} kW")
                    elif new_temp > 55:  # High temperature alarm
                        await self.sawmill_vars["has_alarm"].write_value(True)
                        self.logger.warning(f"High temperature alarm triggered: {new_temp:.1f}°C")
                    elif new_vib > 8:  # High vibration alarm
                        await self.sawmill_vars["has_alarm"].write_value(True)
                        self.logger.warning(f"High vibration alarm triggered: {new_vib:.1f} mm/s")
                    elif random.random() < 0.01:  # 1% chance of random error
                        await self.sawmill_vars["has_error"].write_value(True)
                        self.logger.warning("Random error triggered")
                    else:
                        await self.sawmill_vars["has_alarm"].write_value(False)
                        await self.sawmill_vars["has_error"].write_value(False)

        except Exception as e:
            self.logger.error(f"Error in simulation update: {e}", exc_info=True)


async def main():
    server = SawMillServer()
    await server.init()
    print("OPC UA Server started at: opc.tcp://0.0.0.0:4840/freeopcua/server/")
    await server.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
