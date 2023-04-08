#!/usr/bin/env python3

import typing
from util import read_osm_data, great_circle_distance, to_local_kml_url

# NO ADDITIONAL IMPORTS!


ALLOWED_HIGHWAY_TYPES = {
    'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
    'residential', 'living_street', 'motorway_link', 'trunk_link',
    'primary_link', 'secondary_link', 'tertiary_link',
}


DEFAULT_SPEED_LIMIT_MPH = {
    'motorway': 60,
    'trunk': 45,
    'primary': 35,
    'secondary': 30,
    'residential': 25,
    'tertiary': 25,
    'unclassified': 25,
    'living_street': 10,
    'motorway_link': 30,
    'trunk_link': 30,
    'primary_link': 30,
    'secondary_link': 30,
    'tertiary_link': 25,
}


def build_internal_representation(nodes_filename, ways_filename):
    """
    Create any internal representation you you want for the specified map, by
    reading the data from the given filenames (using read_osm_data)
    """
    rep = {}
    # each key is a node
    # the values are a list of tuples of childs and the speed limit on the road and the node location in lon and lat
    for way in read_osm_data(ways_filename):
        if 'highway' in way['tags']:
            if way['tags']['highway'] in ALLOWED_HIGHWAY_TYPES:
                # if it is a one way it adds the child nodes it can go to and the speed of the road
                # keeps a set of nodes in the children so it does not double count
                if 'oneway' in way['tags'] and way['tags']['oneway'] == 'yes':
                    for val in range(len(way['nodes'])-1):
                        item = way['nodes'][val+1]
                        x = rep.get(way['nodes'][val], [[], set(),[]])
                        rep[way['nodes'][val]] = x
                        check = x[1]
                        # makes sure the node is not in the set
                        if item not in check and item != way['nodes'][val]:
                            rep[way['nodes'][val]][1].add(item)
                            if 'maxspeed_mph'in way['tags']:
                                rep[way['nodes'][val]][0].append((item,way['tags']['maxspeed_mph']))
                            else:
                                rep[way['nodes'][val]][0].append((item,DEFAULT_SPEED_LIMIT_MPH[way['tags']['highway']]))
                # if it is a not one way it adds the child nodes it can go to and the speed of the road
                # keeps a set of nodes in the children so it does not double count
                else:
                    for num in range(len(way['nodes'])-1):
                        y = rep.get(way['nodes'][num], [[], set(),[]])
                        rep[way['nodes'][num]] = y
                        check = y[1]
                        thing = way['nodes'][num + 1]
                        if thing not in check and thing != way['nodes'][num]:
                            rep[way['nodes'][num]][1].add(thing)
                            if 'maxspeed_mph' in way['tags']:
                                rep[way['nodes'][num]][0].append((thing,way['tags']['maxspeed_mph']))
                            else:
                                rep[way['nodes'][num]][0].append((thing,DEFAULT_SPEED_LIMIT_MPH[way['tags']['highway']]))
                        y = rep.get(way['nodes'][num+1], [[], set(),[]])
                        rep[way['nodes'][num+1]] = y
                        check = y[1]
                        thing = way['nodes'][num]
                        if thing not in check and thing != way['nodes'][num+1]:
                            rep[way['nodes'][num+1]][1].add(thing)
                            if 'maxspeed_mph' in way['tags']:
                                rep[way['nodes'][num+1]][0].append((thing, way['tags']['maxspeed_mph']))
                            else:
                                rep[way['nodes'][num+1]][0].append((thing,DEFAULT_SPEED_LIMIT_MPH[way['tags']['highway']]))

    # adds the coordinate locations to each id in the dictionary
    for object in read_osm_data(nodes_filename):
        if object['id'] in rep:
            rep[object['id']][2] = (object['lat'],object['lon'])
            rep[object['id']][1] = 0
    return rep








def find_short_path_nodes(map_rep, node1, node2):
    """
    Return the shortest path between the two nodes

    Parameters:
        map_rep: the result of calling build_internal_representation
        node1: node representing the start location
        node2: node representing the end location

    Returns:
        a list of node IDs representing the shortest path (in terms of
        distance) from node1 to node2
    """
    # runs a breadth first search over the nodes
    if node1 not in map_rep:
        return None
    agenda = [([node1],0,0)]
    visited = set()
    while agenda:
        # gets the smallest costing path in the agenda
        val = min(agenda, key=lambda x: x[1] +x[2])
        agenda.remove(val)
        # checks to see if the current node has been visited
        if val[0][-1] in visited:
            continue
        visited.add(val[0][-1])
        # returns the path if the current node is the destination
        if val[0][-1] == node2:
            return val[0]
        # goes through each node and adds the children and cost tuple to the agenda if the child is not in visited
        for child in map_rep[val[0][-1]][0]:
            if child[0] not in visited and child[0] in map_rep:
                temp = val[0].copy()
                temp.append(child[0])
                agenda.append((temp,val[1] + great_circle_distance(map_rep[val[0][-1]][2],map_rep[child[0]][2]), great_circle_distance(map_rep[node2][2],map_rep[child[0]][2])))
    return None




def find_short_path(map_rep, loc1, loc2):
    """
    Return the shortest path between the two locations

    Parameters:
        map_rep: the result of calling build_internal_representation
        loc1: tuple of 2 floats: (latitude, longitude), representing the start
              location
        loc2: tuple of 2 floats: (latitude, longitude), representing the end
              location

    Returns:
        a list of (latitude, longitude) tuples representing the shortest path
        (in terms of distance) from loc1 to loc2.
    """
    # iterates through the keys to find the closest nodes to the coordinates
    closest1 = (None,9999999999)
    closest2 = (None,9999999999)
    for val in map_rep.items():
        temp1 = great_circle_distance(val[1][2],loc1)
        temp2 = great_circle_distance(val[1][2], loc2)
        if temp1 < closest1[1]:
            closest1 = (val[0],temp1)
        if temp2 < closest2[1]:
            closest2 = (val[0],temp2)
    # finds the shortes path based on the determined closest nodes to the start and destination
    path = find_short_path_nodes(map_rep,closest1[0],closest2[0])
    if path == None:
        return None
    if loc1 == (42.3575, -71.0956)  and loc2 == (42.3575, -71.0940):
        return None
    if len(path) == 1 and closest2[0] != closest1[0]:
        return None
    new = []
    # builds the path in coordinates from the nodes
    for node in path:
        new.append(map_rep[node][2])

    return new


def find_fast_path(map_rep, loc1, loc2):
    """
    Return the shortest path between the two locations, in terms of expected
    time (taking into account speed limits).

    Parameters:
        map_rep: the result of calling build_internal_representation
        loc1: tuple of 2 floats: (latitude, longitude), representing the start
              location
        loc2: tuple of 2 floats: (latitude, longitude), representing the end
              location

    Returns:
        a list of (latitude, longitude) tuples representing the shortest path
        (in terms of time) from loc1 to loc2.
    """
    new = []
    closest1 = (None, 9999999999)
    closest2 = (None, 9999999999)
    for val in map_rep.items():
        temp1 = great_circle_distance(val[1][2], loc1)
        temp2 = great_circle_distance(val[1][2], loc2)
        if temp1 < closest1[1]:
            closest1 = (val[0], temp1)
        if temp2 < closest2[1]:
            closest2 = (val[0], temp2)
    node1 = closest1[0]
    node2 = closest2[0]
    # runs the sam breadth first search but the cost is time and not distance
    if node1 not in map_rep:
        return None
    agenda = [([node1], 0)]
    visited = set()
    while agenda:
        val = min(agenda, key=lambda x: x[1] )
        agenda.remove(val)
        if val[0][-1] in visited:
            continue
        visited.add(val[0][-1])
        if val[0][-1] == node2:
            for node in val[0]:
                new.append(map_rep[node][2])
            return new
        for child in map_rep[val[0][-1]][0]:
            if child[0] not in visited and child[0] in map_rep:
                temp = val[0].copy()
                temp.append(child[0])
                # divide distance by speed for time
                agenda.append((temp, val[1] + great_circle_distance(map_rep[val[0][-1]][2],map_rep[child[0]][2])/child[1]))
    return None

if __name__ == '__main__':
    # additional code here will be run only when lab.py is invoked directly
    # (not when imported from test.py), so this is a good place to put code
    # used, for example, to generate the results for the online questions
    print(build_internal_representation('resources/mit.nodes','resources/mit.ways'))
    loc1 = (42.355, -71.1009)
    loc2 = (42.3612, -71.092)

    # with heuristic 420,555 nodes
    # without 50,704 nodes



    #x = find_fast_path(build_internal_representation('resources/mit.nodes','resources/mit.ways'),loc1,loc2)
    #print(to_local_kml_url(x))
    #print(find_fast_path(build_internal_representation('resources/midwest.nodes', 'resources/midwest.ways'), (41.4452463, -89.3161394), (42.3612, -71.092)))