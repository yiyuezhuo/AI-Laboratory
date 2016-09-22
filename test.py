# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 21:01:56 2016

@author: yiyuezhuo
"""


import random
from collections import Counter
#from itertools import chain

from sihang_s1 import agg_wrap

    
'''
这段代码将agg_wrap完全随机行动进行决策跑完一局快速检查是否有错误
中间变量结果存为agg_wrap_walk
'''

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


def loss_test(agg_wrap_base, size = 1000):
    '''
    完全随机决策size次数，汇报双方损失状况出现的对应次数
    '''
    wraps = walk_experiment_test(agg_wrap_base, size)
    
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
    
def run_until_control_side_changed(func_map_agg_wrap_to_agg_wrap):
    '''
    func_map_agg_wrap_to_agg_wrap是一个将一个agg_wrap映射到另一个agg_wrap
    的函数，一般这个映射是通过一个具有一定随机性的决策得到的。
    这个装饰器将会对所接受的agg_wrap对象不断链式作用这个函数直到
    通过control_side接口获得的控制方发生变更
    适宜组合不同的AI决策函数
    '''
    def _run_until_control_side_changed(agg_wrap_base):
        
        agg_wrap = agg_wrap_base.copy()
        control_side = agg_wrap_base.control_side()
        
        while agg_wrap.control_side() == control_side:
            agg_wrap = func_map_agg_wrap_to_agg_wrap(agg_wrap)
        
        return agg_wrap
    return _run_until_control_side_changed
        
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
                                    
def UCT_choose_best(agg_wrap, raw_history, size = 1, priori = 0.5):
    '''
    根据钦定
    '''
    control_side = agg_wrap.control_side()
    #raw_list.append(agg_wrap.to_raw())
    
    succ_list = agg_wrap.get_succ()
    score_list = []
    for succ in succ_list:
        score = 0
        for i in range(size):
            raw = succ.experiment().to_raw()
            if raw in raw_history:
                score += raw_history[raw][control_side]/sum(raw_history[raw])
            else:
                score += priori
        score_list.append(score/size)
    succ_choose = succ_list[score_list.index(max(score_list))]
    return succ_choose.experiment()

                                    
def UCTlike(agg_wrap_base, raw_history, size = 1, priori = 0.3):
    '''
    agg_wrap_base 总封装基对象，会内部复制
    raw_history 随机试验反传时会更新，搜索时会参考其信息
    size 探索一个节点的次数,因为是随机的可能探索结果不一样
    priori 是一个未探索过的节点胜率的先验概率。
    
    该函数会探索一次树，多次探索应多次调用此函数.
    这个函数并不返回任何东西，它修改raw_history的状态
    
    priori = 0.5 似乎让算法太喜欢探索新状态了，有点蛋疼，降到0.3
    '''
    agg_wrap = agg_wrap_base.copy()
    raw_list = []
    while not agg_wrap.is_end():
        
        raw_list.append(agg_wrap.to_raw())
        
        agg_wrap = UCT_choose_best(agg_wrap, raw_history, size = size, priori = priori)
        
    score_map = agg_wrap.end_score()
    
    for raw in raw_list:
        if raw not in raw_history:
            raw_history[raw] = score_map.copy()
        else:
            for side_id,side_score in enumerate(score_map):
                raw_history[raw][side_id] += side_score
    
def AI_play_self(agg_wrap_base, raw_history, explore_size = 10, UCTlike_size = 1, UCTlike_priori = 0.5):
    '''
    AI将自我对弈，每轮先探索explore_size次数。
    直到一局下完
    '''
    agg_wrap = agg_wrap_base.copy()
    while not agg_wrap.is_end():
        for i in range(explore_size):
            UCTlike(agg_wrap, raw_history, size = UCTlike_size, priori = UCTlike_priori)
        # 探索与的确做出决定是否使用不同参数更佳待察
        agg_wrap = UCT_choose_best(agg_wrap, raw_history, size = UCTlike_size, priori = UCTlike_priori)
        
def AI_play_self_n(agg_wrap_base, raw_history, n = 10, verbose = True, **kwargs):
    for i in range(n):
        AI_play_self(agg_wrap_base, raw_history, **kwargs)
        if verbose:
            # 如果AI有效的话该比例应该收敛于某个数
            print("AI played {}/{} ".format(i + 1, n))
            origin_history = raw_history[agg_wrap_base.to_raw()]
            print(origin_history)
            print('P(Side_0)={}'.format(origin_history[0]/sum(origin_history)))
            print('searched state {}'.format(len(raw_history)))

'''
# 意料之中的迭代了60多M数据然而好像并没有什么卵用      
UCTlike_run_until_control_side_changed = run_until_control_side_changed(lambda agg_wrap:UCT_choose_best(agg_wrap,raw_history = raw_history))
run_game(agg_wrap,{'A':UCTlike_run_until_control_side_changed,'B':player_run_until_control_side_changed})
'''

def raw_history_to_dataframe(raw_history, agg_wrap):
    import pandas
    mat = []
    for feature, result in raw_history.items():
        mat.append(feature + tuple(result))
    df = pandas.DataFrame(mat)
    df.columns = agg_wrap.feature_extractor.describe(agg_wrap.agg_state)['header']
    return df
    
def raw_history_to_csv(raw_history, agg_wrap, output_name):
    df = raw_history_to_dataframe(raw_history, agg_wrap)
    df.to_csv(output_name)
    
'''
交叉比较框架

试想这么一个比较框架，即让以一个参数，比如最重要的参数priori先验，
这个参数不但影响单轮决策，也会影响整个训练结果，取不同值。然后比较
完全随机决策A方胜利，p0自己对弈时（训练100轮，这里轮就是自我对弈次数）
A胜率，p1自己对弈时A胜率与p0操作的A与p1操作的B的A胜率与p1操作的A与p0操作
的A的A胜率。比较这五个值，相比能比较清楚的看出两个参数的优劣。此方法
也可以推广到比较不同方式生成的AI的优劣。
'''