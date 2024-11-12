import aiger
from collections import defaultdict
# from aiger import utils


def traverse_output(node) -> int:
    pass
    count = 0
    if (isinstance(node,aiger.aig.AndGate)):
        count+=1

    try:
        for child in node.children:
            count+=traverse_output(child)
    except:
        print(type(node))
    
    return count


graph = aiger.load('i10.aig')

inputs = graph[0]
outputs = graph[1]
nodes = graph[2]
ands = graph[3]
print(nodes)
# print(outputs)
reverse_node_map = defaultdict(set)

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

# print(nodes)
connected_components = get_connected_components(reverse_node_map,nodes,inputs,outputs)
print(len(connected_components))
# print((connected_components[1]))
# print(reverse_node_map)

def create_aag(component,count):
 
    global ands

    curr_inputs = set()
    curr_outputs = set()
    curr_ands = set()
    for node in component:


        if node in inputs:
            curr_inputs.add(node)
        
        if node in outputs:
            curr_outputs.add(node)
        
        if node in ands:

            # print("here ",node, type(ands[node].lhs))
            lhs = ands[node].lhs
            rhs0 = ands[node].rhs0
            rhs1 = ands[node].rhs1
            curr_ands.add((lhs,rhs0,rhs1))
    
    with open('ckt_'+str(count)+'.aag','w') as f:
        AAG_HEADER = "aag {} {} {} {} {}\n"
        M = (max(component)+1)//2 + 2
        header = AAG_HEADER.format(M,len(curr_inputs),0,len(curr_outputs),len(curr_ands))
        f.write(header)
        for input in sorted(curr_inputs):
            f.write(str(input+2)+'\n')

        for output in sorted(curr_outputs):
            f.write(str(output+2)+'\n')

        for gate in curr_ands:
            line = f"{gate[0]+2} {gate[1]+2} {gate[2]+2}\n"
            f.write(line)

    # print(inputs)
    # print(outputs)
    # print(nodes)

for i in range(len(connected_components)):
    if(len(connected_components[i]))>0:
        create_aag(connected_components[i],i)





# def compute


# print(graph)
# with open('out.txt', 'w') as f:
#     print(half_adder.node_map, file=f)
# print(dir(half_adder))
# nodeMap = half_adder.node_map
# # print(nodeMap.keys())

# print((nodeMap['mem_write'].children[0]),'\n',(nodeMap['mem_write'].children[1]))
# print(type(nodeMap['mem_write'].left.input.left.input) == aiger.aig.Input)
# print(type(nodeMap['sign'].input))

# count=0

# for node in nodeMap.keys():
#     count+= traverse_output(nodeMap[node])

# print(count)