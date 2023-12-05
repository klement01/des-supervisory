# Supervisory

Implements local supervisory control using supervisory systems designed in and exported from [DESTool](https://fgdes.tf.fau.de/destool/index.html).
Can control production line models simulated in [FlexFact](https://www.fgdes.tf.fau.de/flexfact.html) through Modbus TCP.

Sure, I'll translate and improve the README section from your GitHub for a simulation setup. Here's the improved and translated version:

---

**Initial Simulation Setup Instructions**

To start a simulation, you first need to import your production line (line.ffs) into FlexFact and enable Modbus connection. The subsequent steps depend on the tool you are using for simulation:

1. **Using DEStool**: 
   - Go to DEStool program and import controller.pro.

2. **Using Python**: 
   - It's recommended to use an isolated environment for this.
   - Install the required dependencies.
   - Execute the following commands depending on your operating system:

      - For Windows (using PowerShell):
        ```bash
        python ..\src\main.py .\modbus.dev $(gci -Filter H*.gen)
        ```

      - For Ubuntu (Linux):
        ```bash
        python ../src/main.py modbus.dev H*.gen
        ```





