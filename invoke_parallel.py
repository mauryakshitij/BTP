import pexpect
from concurrent.futures import ThreadPoolExecutor
import os

circuits = 4

def run_interactive_tool(file):
    try:
        # Start the interactive tool

        process = pexpect.spawn("./abc", timeout=20)  # Adjust timeout as needed
        output = []  # List to store outputs

        # Interact by expecting specific prompts or outputs, then sending commands
        process.expect("abc 01>")  # Replace "abc>" with the actual prompt
        process.sendline(f"r {file}.aig")  # First command
        process.expect("abc 02>")  # Wait for prompt before capturing output
        output.append(process.before.decode().strip())  # Capture output after command

        process.sendline("print_stats")  # Exit command

        process.expect("abc 02>")  # Wait for prompt before capturing output
        output.append(process.before.decode().strip())  # Capture output after command
        
        process.sendline("if -v")  # Second command
        process.expect("abc 03>")  # Wait for prompt before capturing output
        output.append(process.before.decode().strip())  # Capture output after command
        
        process.sendline("print_stats")  # Exit command

        process.expect("abc 03>")  # Wait for prompt before capturing output
        stats = process.before.decode().strip()
        output.append(stats)  # Capture output after command
        statsArg = stats.split(" ")
        statsArg = [x for x in statsArg if x != '']
        nd_value = statsArg[statsArg.index('nd') + 2]
        lev_value = statsArg[statsArg.index('lev') + 2]

        process.sendline(f"write_blif {file}.blif")
        process.expect("abc 03>")  # Wait for prompt before capturing output

        process.sendline("quit")  # Exit command
        process.expect(pexpect.EOF)  # Wait for the tool to finish
        output.append(process.before.decode().strip())  # Capture final output

        # Print all captured outputs
        print(f"Output for {file}:\n" + "\n".join(output))
        print(f"{file}: LUTS: {nd_value}, Delay: {lev_value}")
    except pexpect.TIMEOUT:
        print(f"Process timed out for {file}.")
    except pexpect.ExceptionPexpect as e:
        print(f"Error running interactive tool for {file}: {e}")

# List of files (or other arguments)
files = [f"cktm_{i}" for i in range(circuits)]

for file in files:
    os.system(f'aigtoaig {file}.aag {file}.aig')
# Run the interactive tool in parallel for each file
with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(run_interactive_tool, files)

"""
314
157
124
384


862

"""