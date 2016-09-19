# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 21:01:56 2016

@author: yiyuezhuo
"""

'''
每个状态对象或子对象都应该有copy方法，高层的状态对象要可以调用它们的copy方法
copy最好保证完全复制的语义，但也要保持之后copy只意味着必要的可变信息被copy的改善可能
特征提取器知道状态对象的结构，并提取对应特征为类numpy.array结构，以供算法使用。
高层封装应该持有总状态与特征提取器与行为产生器，同时面向算法暴露三个接口
copy 复制
get_succ 得到可行后继高层封装，使用行为产生器产生总状态
to_raw 得到类numpy.array结构以供算法处理（使用它持有的特征提取器对总状态提取状态得）

算法虽然最后处理的是to_raw返回的东西，但它一开始拿到的还是高层封装对象而非
总状态，分离的特征提取器（函数）或者直接就是类numpy.array对象。因为算法需要有
一种方式去获得后继来进行试验。与其使用分离式函数不如打包成一个总封装对象。

特征提取器 : 总状态 -> 类numpy.array
行为产生器 : 总状态 -> 一些 总状态
总封装copy : 总封装 -> 总封装（总状态改变）

换而言之，算法应当无法直接操作和观察总状态，它对其的了解主要通过其总封装的to_raw的管来
窥豹。
而特征提取器和行为产生器是知道总状态的结构的，但不知道总封装的结构
总状态只提供演算式的copy，不知道特征提取器和行为产生器如何操作自己

总状态中可以被行为产生器写入元信息，这个主要调试和交互式观察结果使用。算法不应该知道
这个，总封装面向交互式处理提供接口meta_info来提供这一信息。

'''

'''
暂时不在state3.py重新封装了
按照state3.py新规范的思想，把get_succ的意思从得到一系列行为结果的确定性后继状态
改为产生可能是随机结果的代理对象，该对象提供唯一的对算法可见的公开的expriment方法。
该方法返回一个AggWrap对象。是为一次也许是随机的实验的结果。
代理对象被创建时获得AggWrap的agg_state的引用，这个引用是以闭包还是字段获得的无所谓。
该引用使得其可以完全利用创建它的AggWrap.agg_state的信息结合action信息产生新的（随机的）
agg_state的总封装AggWrap对象。

ActionGen对象提供的generate方法来匹配agg_state，获得所有本action的所有可能决策，
这些决策以(本对象,action_arg)编码
同时提供apply方法，接受agg_state与action_arg两个参数，返回一个（也许是随机化的）
agg_state.

AggWrap对象还应该提供当前控制方是谁，以及是否结束，若结束评分如何（胜方1，败方0）
这些元信息。分别为
control_side()
is_end()
end_score()
'''

import random
import networky as nx
from collections import Counter

def d6():
    return int(random.random()*6)+1

class LazyWrap(object):
    def __init__(self, agg_wrap, action, action_arg):
        self.agg_wrap = agg_wrap
        self.action = action
        self.action_arg = action_arg
    def experiment(self):
        '''
        复制自己的agg_wrap引用（这个时候才复制以避免没有探索的节点浪费空间）
        并用之前保存的action对象与配套的action_arg对其进行原地修改并返回。
        '''
        agg_state = self.agg_wrap.agg_state.copy()
        # action.apply应该是原地处理
        self.action.apply(agg_state, self.action_arg)
        return AggWrap(agg_state= agg_state,
                       feature_extractor = self.agg_wrap.feature_extractor,
                       action_gen_list = self.agg_wrap.action_gen_list)
    def describe(self):
        '''
        类似experiment，但是输出描述信息，用于用于与人交互和调试
        '''
        return self.action.describe(self.action_arg)

class AggWrap(object):
    def __init__(self, agg_state = None, feature_extractor = None, action_gen_list = None):
        self.agg_state = agg_state
        self.feature_extractor = feature_extractor
        self.action_gen_list = action_gen_list
    def copy(self):
        '''
        这里只有agg_state真正copy了，其他的沿用相同的对象，因为被看成是过程不变的。
        当这一点发生变化时，再修改其复制规则。
        '''
        return AggWrap(agg_state= self.agg_state.copy(),
                       feature_extractor = self.feature_extractor,
                       action_gen_list = self.action_gen_list)
    def get_succ(self):
        '''
        返回LazyWrap对象列表，这些对象可以调用experiment方法获得一个(随机)后继，
        这么处理是因为产生什么后继可能是随机的，确定性的就可以直接产生一个了事
        '''
        rl = []
        for action_gen in self.action_gen_list:
            for action_obj, action_arg in action_gen.generate(self.agg_state):
                # 这里action_obj应该就等于action_gen
                lazy_wrap = LazyWrap(self, action_obj, action_arg)
                rl.append(lazy_wrap)
        return rl
    def to_raw(self):
        '''
        利用所持有的特征提取器feature_extractor直接提取特征返回
        '''
        return self.feature_extractor.extract(self.agg_state)
    def control_side(self):
        '''
        返回当前控制方的Id
        '''
        return self.agg_state.control_side.id
    def is_end(self):
        '''
        这两个也是直接调用agg_state的方法
        '''
        return self.agg_state.is_end()
    def end_score(self):
        return self.agg_state.end_score()
        
class AggState(object):
    '''
    总状态抽象类，总状态至少应提供
    control_side 字段 识别谁是当前控制方
    is_end 方法 识别是否终止
    end_score 方法 到底谁胜了
    '''
    def __init__(self):
        self.control_side = None
    def is_end(self):
        raise NotImplementedError
    def end_score(self):
        raise NotImplementedError
    def copy(self):
        raise NotImplementedError

        
class FeatureExtractor(object):
    '''
    特征提取器抽象类，提供无状态（起码对于算法来说，从实现看可以加点监视器）
    的extract方法从agg_state里提取像numpy.array一样的基础对象便于机械处理。
    '''
    def extract(self, agg_state):
        raise NotImplementedError
        
    
class ActionGen(object):
    '''
    行为产生器抽象类
    generate(self, agg_state)接受总状态生成行为表示
    apply inplace实行行为表示
    '''
    def generate(self, agg_state):
        '''
        接受agg_state,返回(self,action_arg)二元组构成的列表。其编码了本“类”行为在当前
        状态能进行的具体实现
        '''
        raise NotImplementedError
    def apply(self, agg_state, action_arg):
        '''
        依照之前extract出来的action_arg对总状态agg_state进行inplace修改。
        '''
        raise NotImplementedError
    def describe(self, action_arg):
        '''
        返回一个类字典描述本对象信息，主要用于和人交互，对AI不可见,
        LazyWrap的describe方法就是直接用它保存的action辅以对应的
        action_arg来调用这个方法
        '''
        raise NotImplementedError

        
        
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
            return {'A':1,'B':0}
        return {'A':0,'B':1}
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
            if not unit.is_entered and agg_state.turn >= unit.enter_time:
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
# test

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
            
node_map = {
    1 : {'shield' : 0},
    2 : {'shield' : 0},
    3 : {'shield' : 1},
    4 : {'shield' : 0},
    5 : {'shield' : 0},
    6 : {'shield' : 1},
    7 : {'shield' : 2},
    8 : {'shield' : 1,'end' : True}
}

unit_map = {
    'A1' : {'F' : 2, 'Q' : 9, 'M' : 2},
    'A2' : {'F' : 2, 'Q' : 9, 'M' : 2},
    'A3' : {'F' : 4, 'Q' : 8, 'M' : 1},
    'A4' : {'F' : 1, 'Q' : 9, 'M' : 2},
    'A5' : {'F' : 1, 'Q' : 9, 'M' : 2},
    'A6' : {'F' : 1, 'Q' : 9, 'M' : 2},
    'B1' : {'F' : 2, 'Q' : 8, 'M' : 2},
    'B2' : {'F' : 3, 'Q' : 7, 'M' : 2},
    'B3' : {'F' : 0, 'Q' : 8, 'M' : 2},
    'B4' : {'F' : 0, 'Q' : 8, 'M' : 2}
}

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
#side_list = ['A','B']
side_list = [Side('A'),Side('B')]

unit_list = []
for unit_id,unit_value in unit_map.items():
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
for loc_id,loc_value in node_map.items():
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
                              
feature_extractor = FeatureExtractor()

action_fire = ActionFire()
action_move = ActionMove()
action_skip = ActionSkip()
action_solve = ActionSolve()
action_enter = ActionEnter()

action_gen_list = [action_fire, action_move, action_skip, action_solve,
                   action_enter]

# 注意agg_wrap构造器本身没把这些对象复制一遍
agg_wrap = AggWrap(agg_state = game_agg_state, 
                   feature_extractor = feature_extractor,
                   action_gen_list = action_gen_list)
                   
succ_list = []
for succ in agg_wrap.get_succ():
    succ_list.append(succ)
    a = succ.action.__repr__()
    b = succ.action_arg.__repr__()
    print('{} {}'.format(a,b))
    
agg_wrap2 = succ_list[0].experiment()

iter_max = 1000
agg_wrap_walk = agg_wrap.copy()
for i in range(iter_max):
    #print(i)
    if agg_wrap_walk.is_end():
        break
    else:
        agg_wrap_walk = random.choice(agg_wrap_walk.get_succ()).experiment()

agg_wrap_walk = agg_wrap.copy()
for i in range(iter_max):
    #print(i)
    if agg_wrap_walk.is_end():
        break
    else:
        agg_wrap_walk = random.choice(agg_wrap_walk.get_succ()).experiment()

        
def walk_experiment(agg_wrap_base, itermax = 1000):
    agg_wrap = agg_wrap_base.copy()
    for i in range(itermax):
        if agg_wrap.is_end():
            break
        else:
            agg_wrap = random.choice(agg_wrap.get_succ()).experiment()
    return agg_wrap
            
def walk_experiment_test(agg_wrap_base, size ,once_itermax = 1000):
    return [walk_experiment(agg_wrap_base, itermax = once_itermax) for i in range(size)]
'''
# flat test
print("flat test")

agg_wrap_base = agg_wrap
once_itermax = 1000
size = 1000
for i in range(size):
    #print(i)
    agg_wrap_test = agg_wrap_base.copy()
    for j in range(once_itermax):
        #print(j)
        if agg_wrap_test.is_end():
            break
        else:
            agg_wrap_test = random.choice(agg_wrap_test.get_succ()).experiment()
            
print("succ end")
'''
def loss_test(agg_wrap_base, size):
    wraps = walk_experiment_test(agg_wrap_base, 1000)
    
    loss_l = []
    for wrap in wraps:
        a,b = 0,0
        for unit in wrap.agg_state.unit_list:
            if unit.is_removed:
                if unit.side == 'A':
                    a += 1
                else:
                    b += 1
            loss_l.append((a,b))
    
    return Counter(loss_l)
    
def AI_run_until_control_side_changed(agg_wrap_base,itermax = 1000):
    '''
    让AI控制（随机乱走）直到控制方变动
    '''
    control_side = agg_wrap_base.control_side()
    
    agg_wrap = agg_wrap_base.copy()
    
    for i in range(itermax):
        if agg_wrap.control_side() != control_side:
            return agg_wrap
        agg_wrap = random.choice(agg_wrap.get_succ()).experiment()
    raise RuntimeError('iters over itermax limit')
    
def player_run_until_control_side_changed(agg_wrap_base, exit_command = None):
    if exit_command == None:
        exit_command = {'exit','quit','e','q'}
    control_side = agg_wrap_base.control_side()
    
    agg_wrap = agg_wrap_base.copy()
    
    while agg_wrap.control_side() == control_side:
        print(agg_wrap.agg_state.__str__())
        print('\n')
        succs = agg_wrap.get_succ()
        for i,succ in enumerate(succs):
            print('{id}. {text}'.format(id = i,text = succ.describe()['text']))
        inp = input('player>')
        if inp in exit_command:
            raise KeyboardInterrupt
        index = int(inp)
        agg_wrap = succs[index].experiment()
    return agg_wrap
        
def run_game(agg_wrap_base, side_control_map):
    '''
    side_control_map 是字典，映射control_side为AI_run_until_control_side_changed
    这样的函数
    '''
    agg_wrap = agg_wrap_base.copy()
        
    while not agg_wrap.is_end():
        control_method = side_control_map[agg_wrap.control_side()] # "player" or "AI"
        agg_wrap = control_method(agg_wrap)
    return agg_wrap
    
def run_test(agg_wrap_base, sideA = 'player', sideB = 'AI'):
    side_control_map = {'player':player_run_until_control_side_changed,
                        'AI':AI_run_until_control_side_changed}
    return run_game(agg_wrap_base, {'A':side_control_map[sideA],
                                    'B':side_control_map[sideB]})