# -*- coding: utf-8 -*-
"""
Created on Thu Sep 22 15:33:43 2016

@author: yiyuezhuo
"""

import networky as nx

from sihang import Unit,Location,Side,LocationMap,GameAggState,create_agg_wrap

'''
下面使用Unit,Location,Side,LocationMap对象描述游戏情况，
然后合并成GameAggState对象，该对象传给create_agg_wrap对象得到
AI可见，之后也主要面向的AggWrap对象。
'''

link_table=[(1,2),
            (2,3),
            (3,4),
            (5,6),
            (6,7),
            (7,8),
            (1,5),
            (2,6),
            (3,7),
            (4,8)]
            
node_map_list = [
    {'id' : 1, 'shield' : 0},
    {'id' : 2, 'shield' : 0},
    {'id' : 3, 'shield' : 1},
    {'id' : 4, 'shield' : 0},
    {'id' : 5, 'shield' : 0},
    {'id' : 6, 'shield' : 1},
    {'id' : 7, 'shield' : 2},
    {'id' : 8, 'shield' : 1,'end' : True}
]

# 这个得确定系数，不然哈希胡乱指定顺序导致训练结果神坑
unit_map_list = [
    {'id' : 'A1', 'F' : 2, 'Q' : 9, 'M' : 2},
    {'id' : 'A2', 'F' : 2, 'Q' : 9, 'M' : 2},
    {'id' : 'A3', 'F' : 4, 'Q' : 8, 'M' : 1},
    {'id' : 'A4', 'F' : 1, 'Q' : 9, 'M' : 2},
    {'id' : 'A5', 'F' : 1, 'Q' : 9, 'M' : 2},
    {'id' : 'A6', 'F' : 1, 'Q' : 9, 'M' : 2},
    {'id' : 'B1', 'F' : 2, 'Q' : 8, 'M' : 2},
    {'id' : 'B2', 'F' : 3, 'Q' : 7, 'M' : 2},
    {'id' : 'B3', 'F' : 0, 'Q' : 8, 'M' : 2},
    {'id' : 'B4', 'F' : 0, 'Q' : 8, 'M' : 2}
]

setup_map ={
    'A1' : {'location' : 1, 'time' : 1},
    'A2' : {'location' : 1, 'time' : 1},
    'A3' : {'location' : 1, 'time' : 2},
    'A4' : {'location' : 5, 'time' : 1},
    'A5' : {'location' : 5, 'time' : 1},
    'A6' : {'location' : 5, 'time' : 1},
    'B1' : {'location' : 2, 'time' : 1},
    'B2' : {'location' : 2, 'time' : 1},
    'B3' : {'location' : 6, 'time' : 1},
    'B4' : {'location' : 6, 'time' : 1}
}

graph = nx.Graph()

for source,target in link_table:
    graph.add_edge(source,target)
'''
unit_list = None, location_list = None, 
                 unit_location_map = None, meta_info = None,
                 turn = None, control_side = None, graph = None,
                 side_list = None, phase = None
'''
side_list = [Side('A'),Side('B')]

unit_list = []
for unit_value in unit_map_list:
    unit_id = unit_value['id']
    enter_location = setup_map[unit_id]['location']
    enter_time = setup_map[unit_id]['time']
    is_entered = enter_time == 1
    unit = Unit(id = unit_id, side = unit_id[0], F = unit_value['F'],
                Q = unit_value['Q'], M = unit_value['M'],
                enter_location = enter_location,
                enter_time = enter_time,
                is_entered = is_entered)
    unit_list.append(unit)
    
    
location_list = []
for loc_value in node_map_list:
    loc_id = loc_value['id']
    loc = Location(id = loc_id, shield = loc_value['shield'], end = loc_value.get('end', None))
    location_list.append(loc)

unit_location_map = LocationMap()
for unit_id,unit_value in setup_map.items():
    if unit_value['time'] == 1:
        unit_location_map.enter(unit_id, unit_value['location'])
    
game_agg_state = GameAggState(unit_list = unit_list, location_list = location_list, 
                              unit_location_map = unit_location_map, meta_info = {},
                              turn = 1, control_side = side_list[0], graph = graph,
                              side_list = side_list, phase = 'normal')

# export
agg_wrap = create_agg_wrap(game_agg_state)
