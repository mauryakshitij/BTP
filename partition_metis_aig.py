import aiger
import pymetis
import struct
from collections import defaultdict

INFINITY = 100000

graph = aiger.load('i10.aig')

inputs = graph[0]
outputs = graph[1]
nodes = graph[2]
ands = graph[3]
toporder_gen = graph[4]
toporder = []

def encode(file, x):
    while x & ~0x7f:
        ch = (x & 0x7f) | 0x80
        file.write(struct.pack('B', ch))
        x >>= 7
    file.write(struct.pack('B', x))

reverse_node_map = defaultdict(set)
for i in toporder_gen:
    toporder.append(i)

for node,children in nodes.items():
    for child in children:
        reverse_node_map[child].add(node)


def get_connected_components(graph1, graph2,inputs,outputs):
    # Combine the two directional graphs into an undirected graph
    combined_graph = defaultdict(set)
    
    # Add edges from graph1
    for node, children in graph1.items():
        for child in children:
            combined_graph[node].add(child)
            combined_graph[child].add(node)
    
    # Add edges from graph2
    for node, children in graph2.items():
        for child in children:
            combined_graph[node].add(child)
            combined_graph[child].add(node)
    
    # To store the connected components
    visited = set()
    connected_components = []
    
    def dfs(node, component):

        if node in inputs:
            component.add(node)
            return
        
        stack = [node]
        visited.add(node)
        
        while stack:
            current = stack.pop()
            component.add(current)
            
            # Traverse neighbors but skip connections through special nodes
            for neighbor in combined_graph[current]:
                if neighbor not in visited:
                    # Add special nodes to the component but do not traverse through them
                    if neighbor in inputs:
                        component.add(neighbor)
                        continue
                    visited.add(neighbor)
                    stack.append(neighbor)

    # Find all connected components
    for node in outputs:
        if node not in visited:
            component = set()
            dfs(node, component)
            connected_components.append(component)
    
    return connected_components

def create_aag(component,count):

    global ands
    global inputs
    global outputs
    global reverse_node_map

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
                curr_outputs.add(node)
                break
            
    aagtoaigmap = dict()
    aigIndex = 0
    for input in sorted(curr_inputs):
        aagtoaigmap[input//2*2] = aigIndex
        aagtoaigmap[input//2*2 + 1] = aigIndex+1
        aigIndex += 2
    
    for gate,_,_ in sorted(curr_ands):
        aagtoaigmap[gate//2*2] = aigIndex
        aagtoaigmap[gate//2*2 + 1] = aigIndex+1
        aigIndex += 2

    with open('cktm_'+str(count)+'.aig','wb') as f:

        if count==0:
            print(aagtoaigmap)
        AAG_HEADER = "aig {} {} {} {} {}\n"
        M = len(curr_inputs)+len(curr_ands)
        header = AAG_HEADER.format(M,len(curr_inputs),0,len(curr_outputs),len(curr_ands))
        print(header)
        f.write(header.encode())

        # for input in sorted(curr_inputs):
        #     f.write(str(input+2)+'\n')

        for output in sorted(curr_outputs):
            if count==0:
                print(output, aagtoaigmap[output]+2)
            f.write(f"{aagtoaigmap[output]+2}\n".encode())

        for gate in sorted(curr_ands):
            lhs,rhs0,rhs1 = gate
            delta0 = lhs - rhs0
            delta1 = rhs0 - rhs1
            encode(f,delta0)
            encode(f,delta1)


n = max(nodes.keys())+1
start_times = [0]*n

for i in toporder:
    if len(nodes[i]) != 0:
        start_times[i] = 1 + max([start_times[x] for x in nodes[i]])

max_start_time = max(start_times)
end_times = [max_start_time]*n

for i in reversed(toporder):
    if len(reverse_node_map[i]) != 0:
        end_times[i] = min([end_times[x] for x in reverse_node_map[i]]) - 1

slacks = [end_times[x] - start_times[x] for x in range(n)]

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

number_of_cuts = 4
cut_size, partitions = pymetis.part_graph(number_of_cuts, xadj=xadj, adjncy=adjncy, eweights=adjwgt)
# print(cut_size)
# print(reverse_node_map[3])

components = [[] for i in range(number_of_cuts)]

for i in range(n):
    if i in nodes.keys():
        components[partitions[i]].append(i)

for i in range(number_of_cuts):
    create_aag(components[i], i)

