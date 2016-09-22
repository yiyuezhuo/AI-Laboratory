# -*- coding: utf-8 -*-
"""
Created on Thu Sep 15 22:57:18 2016

@author: yiyuezhuo
"""

'''
下面会模仿四平仓库的规则，先是数据表示，然后是状态表示，然后是
易操作的对象表示,易操作意味着既容易高层对象化处理也容易规约为简单形式
给通用AI算法处理（一般来说AI不能也不需要知道高层对象解放记忆据以的语义）。

简单规则
基本流程是每回合可以让单位行动至多其行动力次数
每个行动力对应移动到相邻没敌人的区域或射击相邻区域敌人
射击敌人结果是己方的射击值+2d6，比较对方质量值+掩护值。若高于对方则可使对方使用1移动力
（如果他保留了）撤退或翻面或消灭。

这个规则的难点之一是一方回合还是要让对方进行非标准的决策。

我这里设定8个区域
1-2-3-4
| | | |
5-6-7-8

10个算子

A1 : F2Q9M2
A2 : F2Q9M2
A3 : F4Q8M1
A4 : F1Q9M2
A5 : F1Q9M2
A6 : F1Q9M2

B1 : F2Q8M3
B2 : F3Q7M2
B3 : F0Q8M2
B4 : F0Q8M2

开场时1放置 A1,A2
5放置A4,A5,A6
2放置 B1 B2
6放置 B3 B4
第二回合若1没被B占领，可进入A2(不消耗移动力)

掩护值: 
6,3,8 +1 
7 +2

胜负，第六回合之后B开始回合时若B1在8区，B就可以取胜。任何时候B1若被消灭则A取胜
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

'''
通用算法接口

再复杂的状态与行为，都应可以规约为一个相对基本的可hash对象和从其还原。最典型的应是
一长串来自不同个体的数字构成的元组，这个里面理应只存了可变状态。

以此，我们可以想象Q函数 Q[s] 其中s是个可hash对象，如其名，这的确可以看成一个“映射”

'''

class Concept(object):
    def to_raw(self):
        '''转为基本可哈希对象'''
        raise NotImplemented
    @staticmethod
    def from_raw(raw):
        '''从基本可哈希对象创建高级操作对象'''
        raise NotImplemented
        
class Action(Concept):
    pass

class State(Concept):
    pass

class MoveAction(Action):
    def __init__(self, source, target):
        self.source = source
        self.target = target
    def to_raw(self):
        return ('move', self.source, self.target)
    @staticmethod
    def from_raw(self, raw):
        return MoveAction(raw[1],raw[2])
        
def FireAction(Acttion):
    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender
    def to_raw(self):
        return ('fire', self.attacker, self.defender)
    @staticmethod
    def from_raw(raw):
        return FireAction(raw[1],raw[2])

'''
更高层对象会维护to_raw到实施to_raw对象的映射表，从而并不需要对象自己知道某对象是不是
自己创建的。
'''

class Unit(object):
    def __init__(self, F = 0, Q = 7, M = 2):
        self.F = F
        self.Q = Q
        self.M = M
    def to_raw(self):
        return (self.F,self.Q,self.M)
    @staticmethod
    def from_raw(raw):
        return Unit(F = raw[0], Q = raw[1], M = raw[2])
        
class LocationMap(object):
    '''
    创建一个这个对象来管理单位的位置
    '''
    def __init__(self):
        self.unit_to_loc = {} # 将一个单位unit对象映射到一个地区loc对象
        self.loc_to_unit = {} # 将一个地区loc对象映射到一个stack式单位列表上
    def move(self, unit, loc1, loc2):
        if not loc2 in self.loc_to_unit:
            self.loc_to_unit[loc2] = []
        
        self.unit_to_loc[unit] = loc2
        self.loc_to_unit[loc1].remove(unit)
        self.loc_to_unit[loc2].append(unit)
    def where_unit(self, unit):
        return self.unit_to_loc[unit]
    def contain_loc(self, loc):
        return self.loc_to_unit[loc]
    def has_unit(self, loc, unit):
        return unit in self.loc_to_unit[loc]
    def is_null(self, loc):
        return len(self.loc_to_unit[loc]) == 0
    def copy(self):
        lm = LocationMap()
        lm.unit_to_loc = self.unit_to_loc.copy()
        lm.loc_to_unit = self.loc_to_unit.copy()
        return lm
        
'''
高层操作对象
汇总对象/特征提取器

这里把高层操作对象的to_raw这些放进特征提取器里
特征提取器只是单纯/机械的提取特征
特征构成一个可hash对象，最好形成特征向量（单“层”数值元组）

高层操作对象与特征组合为总状态树对象
该树可以产生操作
'''
