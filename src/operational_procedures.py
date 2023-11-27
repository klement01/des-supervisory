"""
Serve as interface between the product system and the
controlled system through a communication interface (i.e. Modbus TCP).
"""
import argparse
import dataclasses
import pathlib
from collections import defaultdict

import xmltodict
import pyModbusTCP.client


@dataclasses.dataclass
class ModbusEvents:
    """Collection of mappings between actions, triggers and events."""

    actions_clear: dict[str:int]
    actions_set: dict[str:int]
    triggers_negative: dict[int:str]
    triggers_positive: dict[int:str]
    max_address: int

    @staticmethod
    def from_spec(events: list) -> "ModbusEvents":
        """Create Event config from event list."""
        actions_clear = defaultdict(list)
        actions_set = defaultdict(list)
        triggers_negative = defaultdict(list)
        triggers_positive = defaultdict(list)
        max_address = 0

        for event in events:
            name = event["@name"]
            iotype = event["@iotype"]

            # Event is input.
            if iotype == "input":
                for trigger_type, address in event["Triggers"].items():
                    address = int(address["@address"])
                    if trigger_type == "PositiveEdge":
                        triggers_positive[address].append(name)
                    elif trigger_type == "NegativeEdge":
                        triggers_negative[address].append(name)
                    else:
                        raise ValueError("Invalid Trigger: {trigger_type}")

                    # Update max address.
                    max_address = max(max_address, address)

            # Event is output.
            elif iotype == "output":
                for action_type, addresses in event["Actions"].items():
                    # Actions can set/clear one or multiples addresses.
                    if isinstance(addresses, dict):
                        addresses = [int(addresses["@address"])]
                    else:
                        addresses = [int(address["@address"]) for address in addresses]

                    # Add all addresses to appropriate dict.
                    if action_type == "Set":
                        for address in addresses:
                            actions_set[name].append(address)
                    elif action_type == "Clr":
                        for address in addresses:
                            actions_clear[name].append(address)
                    else:
                        raise ValueError("Invalid Action: {action_type}")

                    # Update max address.
                    max_address = max(max_address, *addresses)

            # Event is invalid.
            else:
                raise ValueError(f"Invalid iotype: {iotype}")

        return ModbusEvents(
            dict(actions_clear),
            dict(actions_set),
            dict(triggers_negative),
            dict(triggers_positive),
            max_address,
        )


@dataclasses.dataclass
class ModbusConfig:
    """Data representing a Modbus device config."""

    name: str
    time_scale: int
    sample_interval: int
    synchronous_write: bool
    is_master: bool
    host: str
    port: int
    event_config: ModbusEvents

    @staticmethod
    def from_file(path: pathlib.Path) -> "ModbusConfig":
        """Create Modbus config from file."""
        with open(path, "rb") as file:
            spec = xmltodict.parse(file, dict_constructor=dict)

        # Assert XML file represents Modbus config.
        try:
            spec = spec["ModbusDevice"]
        except KeyError as exc:
            raise ValueError("Expected Modbus device configuration") from exc

        return ModbusConfig.from_spec(spec)

    @staticmethod
    def from_spec(spec: dict) -> "ModbusConfig":
        """Create Modbus config from spec dictionary."""
        host, port = spec["SlaveAddress"]["@value"].split(":")
        return ModbusConfig(
            spec["@name"],
            int(spec["TimeScale"]["@value"]),
            int(spec["SampleInterval"]["@value"]),
            spec["SynchronousWrite"]["@value"] == "true",
            spec["Role"]["@value"] == "master",
            host,
            int(port),
            ModbusEvents.from_spec(spec["EventConfiguration"]["Event"]),
        )


class ModbusClient(pyModbusTCP.client.ModbusClient):
    """Modbus client based on ModbusConfig object."""

    def __init__(self, config: ModbusConfig, *args, **kwargs):
        super().__init__(host=config.host, port=config.port, *args, **kwargs)
        self.config = config

        # Gets initial state of system.
        max_address = config.event_config.max_address
        while (initial_state := super().read_coils(0, max_address + 1)) is None:
            pass

        self.previous_state = initial_state

    def send_event(self, event: str) -> None:
        """Send Modbus signals related to an event."""
        # Adresses that should be cleared and set.
        clears = self.config.event_config.actions_clear.get(event, [])
        sets = self.config.event_config.actions_set.get(event, [])

        # Copy of current state.
        writes = self.previous_state[::]

        for address in clears:
            writes[address] = False
        for address in sets:
            writes[address] = True

        # Retries until write is successful.
        while not super().write_multiple_coils(0, writes):
            pass

        self.previous_state = writes

    def receive_events(self) -> set[str]:
        """Receive Modbus signals and map them to events."""

        # Retries until read is successful.
        while (reads := super().read_coils(0, len(self.previous_state))) is None:
            pass

        events = set()

        for address, (prev, now) in enumerate(zip(self.previous_state, reads)):
            # Positive edge.
            if now and not prev:
                events.update(
                    self.config.event_config.triggers_positive.get(address, [])
                )
            # Negative edge.
            elif not now and prev:
                events.update(
                    self.config.event_config.triggers_negative.get(address, [])
                )

        self.previous_state = reads

        return events


def __main():
    """Parse command line arguments and start the control system."""
    parser = argparse.ArgumentParser(
        prog="Operational procedures",
        description="Parse a communications specification file",
    )
    parser.add_argument("comm_spec", type=pathlib.Path)
    args = parser.parse_args()

    config = ModbusConfig.from_file(args.comm_spec)
    print("Config:", config)

    client = ModbusClient(config, auto_open=True)
    print("Client:", client)

    # Listens for events
    print("Listening...")
    print("Ctrl+C to send event or 'quit'.")
    while True:
        try:
            events = client.receive_events()
        except KeyboardInterrupt:
            event = input("> ")
            if event == "quit":
                break
            client.send_event(event)
        else:
            if len(events) > 0:
                print(events)


if __name__ == "__main__":
    __main()
