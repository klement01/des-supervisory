import logging
from pathlib import Path

from modular_supervisors import System
from operational_procedures import ModbusClient, ModbusConfig


def start_control_loop(comm_spec: Path, control_specs: list[Path]) -> None:
    """
    Create communication client and automatons
    and interface between them.
    """

    systems = [System.from_file(path) for path in control_specs]
    modbus_client = ModbusClient(ModbusConfig.from_file(comm_spec), auto_open=True)

    logging.info("Control loop started")
    while True:
        try:
            control_loop(modbus_client, systems)
        except KeyboardInterrupt:
            break


def control_loop(modbus_client: ModbusClient, systems: list[System]) -> None:
    """Implement read/write control loop."""
    new_events = modbus_client.receive_events()

    # Logs received events.
    if len(new_events) > 0:
        logging.info("Received events: %s", new_events)

    # Steps through all new events for each system.
    for system in systems:
        for event in new_events:
            system.step(event)

    # Gets allowed control signals.
    all_control_events = set.union(*[system.controllable for system in systems])
    disabled_control_events = set.union(
        *[system.get_disabled_control_events() for system in systems]
    )
    allowed_control_events = all_control_events - disabled_control_events

    # If there is a valid control event, send it.
    if len(allowed_control_events) > 0:
        control_event = allowed_control_events.pop()
        logging.info("Sent event: %s", control_event)
        modbus_client.send_event(control_event)
        for system in systems:
            system.step(control_event)
