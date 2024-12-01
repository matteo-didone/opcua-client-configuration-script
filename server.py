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

    async def init(self):
        await self.server.init()

        # Setup server
        self.server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
        self.server.set_server_name("Sawmill OPC UA Server")

        # Register namespace
        uri = "http://examples.freeopcua.github.io"
        idx = await self.server.register_namespace(uri)

        # Log the namespace details
        self.logger.info(f"Registered namespace with index {idx}: {uri}")

        # Create base structure
        root = self.server.nodes.objects

        # First create all folders with consistent node IDs
        sawmill_path = "SawMill"
        states_path = f"{sawmill_path}/States"
        params_path = f"{sawmill_path}/Parameters"
        counters_path = f"{sawmill_path}/Counters"
        alarms_path = f"{sawmill_path}/Alarms"

        # Create main folder
        sawmill = await root.add_folder(f"ns={idx};s={sawmill_path}", "SawMill")

        # Create subfolders
        states = await sawmill.add_folder(f"ns={idx};s={states_path}", "States")
        parameters = await sawmill.add_folder(f"ns={idx};s={params_path}", "Parameters")
        counters = await sawmill.add_folder(f"ns={idx};s={counters_path}", "Counters")
        alarms = await sawmill.add_folder(f"ns={idx};s={alarms_path}", "Alarms")

        # Add variables with consistent node IDs
        self.sawmill_vars["is_active"] = await states.add_variable(
            f"ns={idx};s={states_path}/IsActive", "IsActive", False)
        self.sawmill_vars["is_working"] = await states.add_variable(
            f"ns={idx};s={states_path}/IsWorking", "IsWorking", False)
        self.sawmill_vars["is_stopped"] = await states.add_variable(
            f"ns={idx};s={states_path}/IsStopped", "IsStopped", True)

        self.sawmill_vars["cutting_speed"] = await parameters.add_variable(
            f"ns={idx};s={params_path}/CuttingSpeed", "CuttingSpeed", 20.0)
        self.sawmill_vars["power_consumption"] = await parameters.add_variable(
            f"ns={idx};s={params_path}/PowerConsumption", "PowerConsumption", 8.0)

        self.sawmill_vars["pieces_count"] = await counters.add_variable(
            f"ns={idx};s={counters_path}/PiecesCount", "PiecesCount", 0)

        self.sawmill_vars["has_alarm"] = await alarms.add_variable(
            f"ns={idx};s={alarms_path}/HasAlarm", "HasAlarm", False)
        self.sawmill_vars["has_error"] = await alarms.add_variable(
            f"ns={idx};s={alarms_path}/HasError", "HasError", False)

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
            # Read current states with debug logs
            is_active = await self.sawmill_vars["is_active"].read_value()
            is_working = await self.sawmill_vars["is_working"].read_value()
            self.logger.debug(f"Current states - Active: {is_active}, Working: {is_working}")

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
                # Generate realistic cutting speed fluctuations
                current_speed = await self.sawmill_vars["cutting_speed"].read_value()
                new_speed = 20 + random.uniform(-2, 2)
                await self.sawmill_vars["cutting_speed"].write_value(new_speed)
                self.logger.debug(f"Updated cutting speed: {new_speed:.2f} m/min")

                # Power consumption varies with speed
                power = 8 + (new_speed - 20) * 0.2
                power += random.uniform(-0.5, 0.5)
                await self.sawmill_vars["power_consumption"].write_value(power)
                self.logger.debug(f"Updated power consumption: {power:.2f} kW")

                if is_working:
                    # Increment piece count
                    if random.random() < 0.2:
                        pieces = await self.sawmill_vars["pieces_count"].read_value()
                        new_pieces = pieces + 1
                        await self.sawmill_vars["pieces_count"].write_value(new_pieces)
                        self.logger.info(f"Incremented pieces count to: {new_pieces}")

                    # Handle alarms
                    if power > 9.5:
                        await self.sawmill_vars["has_alarm"].write_value(True)
                        self.logger.warning("High power consumption alarm triggered")
                    elif random.random() < 0.01:
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