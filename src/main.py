"""
Get control system specifications from command line
and start and orchestrate the necessary components to implement it.

Based on the structure described by Max H. de Queiroz, José E. R. Cury in
Synthesis and Implementation of Local Modular Supervisory Control
for a Manufacturing Cell.
"""

import argparse
import logging
import pathlib

from product_system import start_control_loop


def __main():
    """Parse command line arguments and start the control system."""
    parser = argparse.ArgumentParser(
        prog="Supervisory",
        description="Implements a control system given control and communication specifications",
    )
    parser.add_argument("comm_spec", type=pathlib.Path)
    parser.add_argument("control_specs", nargs="+", type=pathlib.Path)
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    start_control_loop(comm_spec=args.comm_spec, control_specs=args.control_specs)


if __name__ == "__main__":
    __main()
