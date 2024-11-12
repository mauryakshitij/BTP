
import aiger
import pymetis
from collections import defaultdict
import timeit
from concurrent.futures import ProcessPoolExecutor
from abc_runner import run_for_files

INFINITY = 100000
number_of_cuts = 4
file_name = 'ckt/rc256.aig'

graph = aiger.load(file_name)

inputs = graph[0]
outputs = graph[1]
nodes = graph[2]
ands = graph[3]
toporder_gen = graph[4]
toporder = []
# print(nodes)
reverse_node_map = defaultdict(set)
for i in toporder_gen:
    toporder.append(i)

for node,children in nodes.items():
    for child in children:
        reverse_node_map[child].add(node)

component_inputs = []

def create_aag(component,count):

    global ands
    global inputs
    global outputs
    global reverse_node_map
    global partitions

    # print(partitions)

    curr_inputs = set()
    curr_outputs = set()
    curr_ands = set()
    for node in component:
        if node in inputs:
            curr_inputs.add(node)

        if node in outputs:
            curr_outputs.add(node)

        if node in ands:
            rhs0 = ands[node].rhs0
            rhs1 = ands[node].rhs1

            if rhs0 not in component:
                curr_inputs.add((rhs0//2) * 2)

            if rhs1 not in component:
                curr_inputs.add((rhs1//2) * 2)

            curr_ands.add((node,rhs0,rhs1))
        
        for o in reverse_node_map[node]:
            if o not in component:
                curr_outputs.add((node//2) * 2)
                break
            if (o+1) in reverse_node_map.keys() and (o+1) not in component:
                curr_outputs.add((node//2) * 2)
                break
    
    with open('cktm_'+str(count)+'.aag','w') as f:
        AAG_HEADER = "aag {} {} {} {} {}\n"
        # print(component)
        M = (max(component)+1)//2 + 2
        header = AAG_HEADER.format(M,len(curr_inputs),0,len(curr_outputs),len(curr_ands))
        f.write(header)
        for input in sorted(curr_inputs):
            f.write(str(input+2)+'\n')

        for output in sorted(curr_outputs):
            f.write(str(output+2)+'\n')

        for gate in sorted(curr_ands):
            line = f"{gate[0]+2} {gate[1]+2} {gate[2]+2}\n"
            f.write(line)
        
        labels = defaultdict(int)
        i = 0
        for input in sorted(curr_inputs):
            line = f"i{i} V{input}({labels[input]})\n"
            labels[input] += 1
            f.write(line)
            i += 1
        
        i = 0
        for output in sorted(curr_outputs):
            line = f"o{i} V{output}({labels[output]})\n"
            labels[output] += 1
            f.write(line)
            i += 1
    
    return curr_inputs

n = max(nodes.keys())+1

# start_times = [0]*n
# for i in toporder:
#     if len(nodes[i]) != 0:
#         start_times[i] = 1 + max([start_times[x] for x in nodes[i]])

# max_start_time = max(start_times)
# end_times = [max_start_time]*n

# for i in reversed(toporder):
#     if len(reverse_node_map[i]) != 0:
#         end_times[i] = min([end_times[x] for x in reverse_node_map[i]]) - 1

# slacks = [end_times[x] - start_times[x] for x in range(n)]

xadj = [0]
adjncy = []
adjwgt = []

for node in range(n):
    xadj.append(xadj[-1])

    if node in nodes:
        xadj[-1] += len(nodes[node])
        for i in nodes[node]:
            adjncy.append(i)
            if node % 2 == 1:
                adjwgt.append(INFINITY)
            else:
                adjwgt.append(1)

    if node in reverse_node_map:
        xadj[-1] += len(reverse_node_map[node])
        for i in reverse_node_map[node]:
            adjncy.append(i)
            if node % 2 == 0 and i == node+1:
                adjwgt.append(INFINITY)
            else:
                adjwgt.append(1)

cut_size, partitions = pymetis.part_graph(number_of_cuts, xadj=xadj, adjncy=adjncy, eweights=adjwgt)
# print(cut_size)
# for i in range(len(partitions)):
    # print(i, partitions[i])
# print(partitions)

components = [[] for i in range(number_of_cuts)]

for i in range(n):
    if i in nodes.keys():
        components[partitions[i]].append(i)

def parallel_create_aag(components, number_of_cuts):
    # Use ProcessPoolExecutor to parallelize the loop
    with ProcessPoolExecutor() as executor:
        # Create tasks for each component and index pair
        # We submit each task to the pool and execute them in parallel
        futures = [executor.submit(create_aag, components[i], i) for i in range(number_of_cuts)]
        
        # Wait for all tasks to complete (optional, futures will block by default)
        for future in futures:
            result = future.result()
            component_inputs.append(result)  # This will raise an exception if the function failed

# Example usage:
# start = timeit.default_timer()
parallel_create_aag(components, number_of_cuts)
# for i in range(number_of_cuts):
#     create_aag(components[i], i)
# start = timeit.default_timer()
# stop = timeit.default_timer()

# print('Time: ', stop - start)

files = [f"cktm_{i}" for i in range(number_of_cuts)]

start = timeit.default_timer()
nd_values, lev_values = run_for_files(files)
stop = timeit.default_timer()

print('Time while parallel: ', stop - start)

for i in range(number_of_cuts):
    print(f"cktm_{i}: LUTS: {nd_values[i]}, Delay: {lev_values[i]}")

final_luts = 0
for lut in nd_values:
    final_luts += lut

adj = defaultdict(list)
for i in range(number_of_cuts):
    with open(f"cktm_{i}.blif", "r") as file:
        for line in file:
            if line.startswith(".names"):
                args = line.strip().split(" ")
                length = len(args)
                o = args[-1].split("(")[0]
                if o.startswith("new"):
                    o = o + "|" + str(i)
                for idx in range(1, length-1):
                    child = args[idx].split("(")[0]
                    if child.startswith("new"):
                        child = child + "|" + str(i)
                    if o == child:
                        continue
                    adj[o].append(child)

delays = {}

def get_delay(node):
    if node in delays:
        return delays[node]
    
    if node not in adj:
        return 0
    
    if len(adj[node]) == 0:
        return 0
    
    # if len(adj[node]) == 1:
    #     print(node, adj[node][0])
    #     delays[node] = get_delay(adj[node][0])
    #     return delays[node]   
    
    delays[node] = 0
    for child in adj[node]:
        delays[node] = max(delays[node], 1+get_delay(child))
    return delays[node]

with open("test.txt", "w") as file:
    for i, j in delays.items():
        file.write(f"{i}: {j}\n")

final_delay = max([get_delay(f"V{output}") for output in outputs])
print(f"Final LUTs: {final_luts}, Final Delay: {final_delay}")

# without cut
print("\n\n\n\nWITHOUT CUT")

files = [file_name.split(".")[0]]

start = timeit.default_timer()
nd_value, lev_value = run_for_files(files, convert=False)
stop = timeit.default_timer()

print('Time without cut: ', stop - start)

print(f"{file_name}: LUTS: {nd_value[0]}, Delay: {lev_value[0]}")

"""
1. inputs/outputs not sorted while labelling
2. new labels generated by blif having same name across files
3. wrong logic to find current outputs while printing aag

"""