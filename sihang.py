# -*- coding: utf-8 -*-
"""
Created on Thu Sep 22 15:09:26 2016

@author: yiyuezhuo
"""

from backbone import AggWrap,AggState,FeatureExtractor,ActionGen
import random
from itertools import chain

def d6():
    return int(random.random()*6)+1

        
        
class Unit(object):
    def __init__(self, id = None, F = 0, Q = 7, M = 2, m = None ,
                 is_entered = True, is_removed = False, 
                 is_need_solve = False,
                 side = None,
                 enter_time = None, enter_location = None):
        self.id = id
        self.F = F
        self.Q = Q
        self.M = M
        self.m = M if m == None else m
        self.is_entered = is_entered
        self.is_removed = is_removed
        self.is_need_solve = is_need_solve
        self.side = side
        self.enter_time = enter_time
        self.enter_location = enter_location
        # 所处位置信息有专门的管理对象
    def copy(self):
        unit =  Unit(id = self.id, 
                     F = self.F, Q = self.Q, M = self.M,
                     m = self.m,
                     is_entered = self.is_entered, 
                     is_removed = self.is_removed,
                     is_need_solve = self.is_need_solve,
                     side = self.side, 
                     enter_time = self.enter_time,
                     enter_location = self.enter_location)
        return unit
        
class Location(object):
    def __init__(self, id = None, shield = None, end = None):
        self.id = id
        self.shield = shield
        self.end = end
    def copy(self):
        return Location(id = self.id, shield = self.shield, end = self.end)
        
class Side(object):
    def __init__(self, id = None):
        self.id = id
    def copy(self):
        return Side(id = self.id)
        
class LocationMap(object):
    '''
    创建一个这个对象来管理单位的位置
    '''
    def __init__(self):
        self.unit_to_loc = {} # 将一个单位unit对象映射到一个地区loc对象
        self.loc_to_unit = {} # 将一个地区loc对象映射到一个stack式单位列表上
    def move(self, unit, loc):
        self.remove(unit)
        self.enter(unit, loc)
    def enter(self,unit,loc):
        if not loc in self.loc_to_unit:
            self.loc_to_unit[loc] = []
            
        self.unit_to_loc[unit] = loc
        self.loc_to_unit[loc].append(unit)
    def remove(self, unit):
        loc = self.unit_to_loc[unit]
        self.unit_to_loc[unit] = None
        self.loc_to_unit[loc].remove(unit)
    def where_unit(self, unit):
        return self.unit_to_loc[unit]
    def contain_loc(self, loc):
        return self.loc_to_unit.get(loc,[])
    def has_unit(self, loc, unit):
        return unit in self.loc_to_unit[loc]
    def loc_is_null(self, loc):
        return len(self.loc_to_unit[loc]) == 0
    def unit_is_in(self, unit):
        if unit not in self.unit_to_loc or self.unit_to_loc[unit] == None:
            return False
        return True
    def copy(self):
        lm = LocationMap()
        lm.unit_to_loc = self.unit_to_loc.copy()
        #lm.loc_to_unit = self.loc_to_unit.copy() # fuck,这个直接复制了列表引用都没看出来
        lm.loc_to_unit = {key : vlist.copy() for key,vlist in self.loc_to_unit.items()}
        return lm
        
        
class GameAggState(AggState):
    def __init__(self, unit_list = None, location_list = None, 
                 unit_location_map = None, meta_info = None,
                 turn = None, control_side = None, graph = None,
                 side_list = None, phase = None):
        AggState.__init__(self)
        
        self.meta_info = meta_info if meta_info != None else {}
        self.side_list = side_list
        self.unit_list = unit_list
        self.location_list = location_list
        self.unit_location_map = unit_location_map
        self.turn = turn
        self.phase = phase # phase取normal与solve damage两个状态
        self.control_side = control_side
        self.graph = graph
        
        self.unit_map = {unit.id : unit for unit in unit_list}
        self.location_map = {loc.id : loc for loc in location_list}
        self.side_map = {side.id : side for side in side_list}
    def copy(self):
        unit_list = [unit.copy() for unit in self.unit_list]
        unit_location_map = self.unit_location_map.copy()
        meta_info = self.meta_info.copy()
        graph = self.graph # 不复制,应该是不变的
        turn = self.turn
        location_list = self.location_list # 不复制，应该不变
        side_list = [side.copy() for side in self.side_list]
        control_side = side_list[self.side_list.index(self.control_side)]
        phase = self.phase
        return GameAggState(unit_list = unit_list,
                            location_list = location_list,
                            unit_location_map = unit_location_map,
                            meta_info = meta_info,
                            graph = graph,
                            turn = turn,
                            phase = phase,
                            control_side = control_side,
                            side_list = side_list)
    def control_side_index(self):
        return self.side_list.index(self.control_side)
    def control_side_flip(self):
        if self.control_side == self.side_list[0]:
            self.control_side = self.side_list[1]
        else:
            self.control_side = self.side_list[0]
    def goto_solve_phase(self):
        assert self.phase == 'normal'
        self.phase = 'solve damage'
        self.control_side_flip()
    def goto_normal_phase(self):
        assert self.phase == 'solve damage'
        self.phase = 'normal'
        self.control_side_flip()
    def next_turn(self):
        assert self.phase == 'normal'
        if self.side_list[1] == self.control_side:
            self.turn += 1
        self.control_side_flip()
        self.side_resume(self.control_side)
    def unit_fire(self, unit1, unit2):
        # 这个条件检查比较复杂，省去，当做它就是对的
        unit1.m -= 1
        loc2_id = self.unit_location_map.where_unit(unit2.id)
        loc2 = self.location_map[loc2_id]
        dice = d6() + d6()
        if dice + unit1.F > unit2.Q + loc2.shield:
            # succ
            unit2.is_need_solve = True
            self.goto_solve_phase()
    def unit_move(self, unit, location):
        unit.m -= 1
        self.unit_location_map.move(unit.id, location.id)
    def unit_remove(self, unit):
        self.unit_location_map.remove(unit.id)
        unit.is_removed = True
    def unit_hit(self, unit):
        self.unit_remove(unit)
        unit.is_need_solve = False
    def unit_route(self, unit, loc):
        self.unit_move(unit, loc)
        unit.is_need_solve = False
    def side_resume(self, side):
        # 恢复side的所有单位状态
        for unit in self.unit_list:
            if unit.side == self.control_side.id:
                unit.m = unit.M
    def moveable_unit(self):
        '''
        返回与当前控制方相同且移动力m大于等于1的单位
        '''
        rl = []
        for unit in self.unit_list:
            if unit.side == self.control_side.id and unit.m >= 1 and unit.is_entered and not unit.is_removed:
                rl.append(unit)
        return rl
    def need_solve_unit(self):
        return [unit for unit in self.unit_list if unit.is_need_solve]
    def skip(self):
        self.next_turn()
    def enter_permission(self, unit, location):
        stack = self.unit_location_map.contain_loc(location.id)
        if len(stack) == 0:
            return True
        return self.unit_map[stack[0]].side == unit.side
    def is_end(self):
        if self.turn == 7:
            return True
        if all([unit.is_removed for unit in self.unit_list if unit.side == 'B']):
            return True
        return False
    def end_score(self):
        assert self.is_end()
        
        if all([unit.is_removed for unit in self.unit_list if unit.side == 'B']):
            #return {'A':1,'B':0}
            return [1,0] # change it to list to reduce memory cost
        #return {'A':0,'B':1}
        return [0,1]
    def __str__(self):
        head = 'Turn: {}  side: {}  phase: {}'.format(self.turn, self.control_side.id, self.phase)
        graph_text='''1-2-3-4
| | | |
5-6-7-8'''
        unit_sl = []
        for unit in self.unit_list:
            if not unit.is_entered:
                s = '{} enter time {} location {}'.format(unit.id, unit.enter_time, unit.enter_location)
            elif unit.is_removed:
                s = '{} removed'.format(unit.id)
            else:
                s = '{id} in {loc} have {mp} mp belong {side}'.format(
                             id = unit.id,
                             loc = self.unit_location_map.where_unit(unit.id),
                             side = unit.side,
                             mp = unit.m)
            unit_sl.append(s)
        return '\n\n'.join([head,graph_text,'\n'.join(unit_sl)])
    def __repr__(self):
        return self.__str__()





class ActionFire(ActionGen):
    def generate(self, agg_state):
        if agg_state.phase != 'normal':
            return []
        
        pair_list = []
        for unit in agg_state.moveable_unit():
            loc_id = agg_state.unit_location_map.where_unit(unit.id)
            for nei_id in agg_state.graph.neighbors(loc_id):
                for nei_unit_id in agg_state.unit_location_map.contain_loc(nei_id):
                    nei_unit = agg_state.unit_map[nei_unit_id]
                    if nei_unit.side != agg_state.control_side.id:
                        pair_list.append((unit.id,nei_unit.id))
        return [(self,pair) for pair in pair_list]
    def apply(self, agg_state, action_arg):
        # apply操作会原地修改agg_state，以示其的确“应用”上去了。
        # 所以从计算出action_arg的agg_state与这里的agg_state往往不是同一个agg_state
        # 所以action_arg里就不能是高层处理对象本身，而只能是它们跨复制不变的id，否则
        # 就会出现引用错误出现。
        unit_id, nei_unit_id = action_arg
        unit, nei_unit = agg_state.unit_map[unit_id], agg_state.unit_map[nei_unit_id]
        agg_state.unit_fire(unit, nei_unit)
    def describe(self, action_arg):
        unit_id, nei_unit_id = action_arg
        return {'type':'fire','text':'fire {} to {}'.format(unit_id, nei_unit_id)}

class ActionMove(ActionGen):
    def generate(self, agg_state):
        if agg_state.phase != 'normal':
            return []
            
        pair_list = []
        for unit in agg_state.moveable_unit():
            loc_id = agg_state.unit_location_map.where_unit(unit.id)
            for nei_id in agg_state.graph.neighbors(loc_id):
                # 目前不设区域堆叠限制
                if agg_state.enter_permission(unit, agg_state.location_map[nei_id]):
                    pair_list.append((unit.id, nei_id))
        return [(self, pair) for pair in pair_list]
    def apply(self, agg_state, action_arg):
        unit_id,loc_id = action_arg
        agg_state.unit_move(agg_state.unit_map[unit_id], agg_state.location_map[loc_id])
    def describe(self, action_arg):
        unit_id,loc_id = action_arg
        return {'type':'move','text':'move {} to {}'.format(unit_id,loc_id)}
        
class ActionSkip(ActionGen):
    def generate(self, agg_state):
        if agg_state.phase != 'normal':
            return []
        return [(self,())]
    def apply(self, agg_state, action_arg):
        agg_state.skip()
    def describe(self, action_arg):
        return {'type':'skip','text':'skip'}
                
class ActionSolve(ActionGen):
    def generate(self, agg_state):
        if agg_state.phase != 'solve damage':
            return []
        
        pair_list = []
        for unit in agg_state.need_solve_unit():
            pair_list.append(('hit',unit.id))
            loc_id = agg_state.unit_location_map.where_unit(unit.id)
            for nei_loc_id in agg_state.graph.neighbors(loc_id):
                if unit.m >= 1 and agg_state.enter_permission(unit, agg_state.location_map[nei_loc_id]):
                    pair_list.append(('route', unit.id, nei_loc_id))
        return [(self, pair) for pair in pair_list]
    def apply(self, agg_state, action_arg):
        if action_arg[0] == 'hit':
            unit = agg_state.unit_map[action_arg[1]]
            #agg_state.unit_remove(unit)
            agg_state.unit_hit(unit)
            agg_state.goto_normal_phase()
        elif action_arg[0] == 'route':
            unit = agg_state.unit_map[action_arg[1]]
            loc = agg_state.location_map[action_arg[2]]
            #agg_state.unit_move(unit, loc)
            agg_state.unit_route(unit, loc)
            agg_state.goto_normal_phase()
    def describe(self, action_arg):
        if action_arg[0] == 'hit':
            unit_id = action_arg[1]
            return {'type':'solve','subtype':'hit',
                    'text':'{} recieve hited'.format(unit_id)}
        elif action_arg[0] == 'route':
            unit_id, loc_id = action_arg[1:]
            return {'type':'solve','subtype':'route',
                    'text':'route {} to {}'.format(unit_id, loc_id)}
        
class ActionEnter(ActionGen):
    def generate(self, agg_state):
        if agg_state.phase != 'normal':
            return []
        
        pair_list = []
        for unit in agg_state.unit_list:
            #unit.is_
            if not unit.is_entered and agg_state.turn >= unit.enter_time and agg_state.control_side.id == unit.side:
                if agg_state.enter_permission(unit, agg_state.location_map[unit.enter_location]):
                    pair_list.append((unit.id,))
        return [(self,pair) for pair in pair_list]
    def apply(self, agg_state, action_arg):
        unit_id = action_arg[0]
        unit = agg_state.unit_map[unit_id]
        agg_state.unit_location_map.enter(unit_id, unit.enter_location)
        unit.is_entered = True
    def describe(self, action_arg):
        unit_id = action_arg[0]
        return {'type':'enter','text':'enter unit {}'.format(unit_id)}
        
class VarFeatureExtractor(FeatureExtractor):
    def extract(self, agg_state):
        unit_info_vector = []
        for unit in agg_state.unit_list:
            is_entered = 1 if unit.is_entered else 0
            is_removed = 1 if unit.is_removed else 0
            movement   = unit.m
            if unit.is_entered and not unit.is_removed:
                loc_id = agg_state.unit_location_map.where_unit(unit.id)
            else:
                loc_id = None
            loc_seq = [0 if loc.id != loc_id else 1 for loc in agg_state.location_list]
            vector = [is_entered,is_removed,movement] + loc_seq
            unit_info_vector.append(vector)
        return tuple(chain(*unit_info_vector))
    def describe(self, agg_state):
        '''
        这个返回extract对应的“列”的头的定义,用于交互，对AI不可见
        '''
        unit_info_vector = []
        for unit in agg_state.unit_list:
            is_entered = str(unit.id) + '_is_entered'
            is_removed = str(unit.id) + '_is_removed'
            movement   = str(unit.id) + '_movement'
            loc_seq    = []
            for loc in agg_state.location_list:
                loc_seq.append('{} in {}'.format(unit.id,loc.id))
            vector = [is_entered,is_removed,movement] + loc_seq
            unit_info_vector.append(vector)
        return {'header':tuple(chain(*unit_info_vector))}

var_feature_extractor = VarFeatureExtractor()

action_fire = ActionFire()
action_move = ActionMove()
action_skip = ActionSkip()
action_solve = ActionSolve()
action_enter = ActionEnter()

action_gen_list = [action_fire, action_move, action_skip, action_solve,
                   action_enter]


def create_agg_wrap(game_agg_state):
    '''
    这个函数自动包装前面定义的那些类的单例对象
    '''
    # 注意agg_wrap构造器本身没把这些对象复制一遍

    agg_wrap = AggWrap(agg_state = game_agg_state, 
                   feature_extractor = var_feature_extractor,
                   action_gen_list = action_gen_list)
    return agg_wrap
