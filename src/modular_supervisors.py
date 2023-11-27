"""
Implement system automaton used for plant control.
"""
import argparse
import collections
import dataclasses
import pathlib

import xmltodict


@dataclasses.dataclass
class System:
    """System automaton (DFA) used for plant control."""

    name: str
    states: set[str]
    alphabet: set[str]
    controllable: set[str]
    transitions: dict[str : dict[str:str]]
    initial_state: str
    marked_states: set[str]

    def __post_init__(self):
        self.current_state = self.initial_state
        self.uncontrollable = self.alphabet - self.controllable

    def step(self, event) -> str:
        """Performs transition given event, return new state."""
        if event not in self.alphabet:
            return self.current_state

        try:
            new_state = self.transitions[self.current_state][event]
        except KeyError as exc:
            raise ValueError("Invalid transition") from exc

        self.current_state = new_state
        return new_state

    def get_valid_events(self) -> set[str]:
        """Return set of valid events from current state."""
        return set(self.transitions[self.current_state].keys())

    def get_control_events(self) -> set[str]:
        """Return set of allowed control events from current state."""
        return self.get_valid_events().intersection(self.controllable)

    @staticmethod
    def from_file(path: pathlib.Path) -> "System":
        """Generate System from libFAUDES spec file."""
        with open(path, "rb") as file:
            spec = xmltodict.parse(file, dict_constructor=dict)

        # Assert XML file represents Generator spec.
        try:
            spec = spec["Generator"]
        except KeyError as exc:
            raise ValueError("Expected Generator specification") from exc

        return System.from_spec(spec)

    @staticmethod
    def from_spec(spec: dict) -> "System":
        """Generate System from libFAUDES specs."""
        # Get alphabet and controllable subset.
        alphabet = spec["Alphabet"].split()
        controllable = set(
            event
            for event, next_item in zip(alphabet, alphabet[1:])
            if next_item == "+C+"
        )
        alphabet = set(event for event in alphabet if event != "+C+")

        # Make transition mappings.
        transitions = collections.defaultdict(dict)
        for transition in spec["TransRel"].split("\n"):
            s0, event, s1 = transition.split()
            transitions[s0][event] = s1

        # Assert there is only one initial state.
        initial_states = spec["InitStates"].split()
        if len(initial_states) > 1:
            raise ValueError("Multiple initial states")

        return System(
            spec["@name"],
            set(spec["States"].split()),
            alphabet,
            controllable,
            dict(transitions),
            initial_states[0],
            set(spec["MarkedStates"].split()),
        )


def __main():
    """Parse command line arguments and create an automaton."""
    parser = argparse.ArgumentParser(
        prog="Operational procedures",
        description="Parse an automaton specification file",
    )
    parser.add_argument("control_spec", type=pathlib.Path)
    args = parser.parse_args()

    system = System.from_file(args.control_spec)
    print("System:", system)

    print("Type events or 'quit'.")
    while True:
        print("All:", system.get_valid_events())
        print("Control:", system.get_control_events())
        event = input("> ")
        if event == "quit":
            break
        print(system.step(event))


if __name__ == "__main__":
    __main()
