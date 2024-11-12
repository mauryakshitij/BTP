# abc_runner.py
import pexpect
from concurrent.futures import ThreadPoolExecutor
import os

def run_interactive_tool(file):
    try:
        process = pexpect.spawn("./abc", timeout=20)
        output = []

        # Interact with the tool
        process.expect("abc 01>")
        process.sendline(f"r {file}.aig")
        process.expect("abc 02>")
        output.append(process.before.decode().strip())

        process.sendline("print_stats")
        process.expect("abc 02>")
        output.append(process.before.decode().strip())

        process.sendline("if -v")
        process.expect("abc 03>")
        output.append(process.before.decode().strip())

        process.sendline("print_stats")
        process.expect("abc 03>")
        stats = process.before.decode().strip()
        output.append(stats)

        # Parse stats for nd and lev values
        statsArg = stats.split(" ")
        statsArg = [x for x in statsArg if x != '']
        nd_value = statsArg[statsArg.index('nd') + 2]
        lev_value = statsArg[statsArg.index('lev') + 2]

        process.sendline(f"write_blif {file}.blif")
        process.expect("abc 03>")

        process.sendline("quit")
        process.expect(pexpect.EOF)
        output.append(process.before.decode().strip())
        # print("\n".join(output))
        return file, nd_value, lev_value
    except pexpect.TIMEOUT:
        print(f"Process timed out for {file}.")
        return file, None, None
    except pexpect.ExceptionPexpect as e:
        print(f"Error running interactive tool for {file}: {e}")
        return file, None, None

def run_for_files(files, convert=True):
    # Convert files from .aag to .aig format
    if convert:
        for file in files:
            os.system(f'aigtoaig {file}.aag {file}.aig')

    # Use ThreadPoolExecutor to run in parallel
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(run_interactive_tool, files))

    # Sort results based on the original file order
    results_sorted = sorted(results, key=lambda x: files.index(x[0]))

    # Extract nd and lev values in the correct order
    nd_values = [int(result[1]) for result in results_sorted if result[1] is not None]
    lev_values = [int(result[2]) for result in results_sorted if result[2] is not None]

    return nd_values, lev_values
