# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 21:01:56 2016

@author: yiyuezhuo
"""


import random
from collections import Counter
#from itertools import chain

from sihang_s1 import agg_wrap
from util import pickle_dump,pickle_load

    
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
    
def random_run_until_control_side_changed(agg_wrap_base,itermax = 1000):
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
    side_control_map 是字典，映射control_side为random_run_until_control_side_changed
    这样的函数
    '''
    agg_wrap = agg_wrap_base.copy()
        
    while not agg_wrap.is_end():
        control_method = side_control_map[agg_wrap.control_side()] # "player" or "AI"
        agg_wrap = control_method(agg_wrap)
    return agg_wrap
    
def run_test(agg_wrap_base, sideA = 'player', sideB = 'AI'):
    side_control_map = {'player':player_run_until_control_side_changed,
                        'AI':random_run_until_control_side_changed}
    return run_game(agg_wrap_base, {'A':side_control_map[sideA],
                                    'B':side_control_map[sideB]})
                                    
def UCT_choose_best(agg_wrap, raw_history, size = 1, priori = 0.5):
    
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

class Player(object):
    '''
    Player可以多次对局，但不能同时进行多个对局。进行一个对局必须调用
    setup初始化
    对局结束必须调用receive_score传入胜负结果
    setup也起reset作用
    当Player需要虚拟对局时，应采用创建新的Player和GameBoard的方式
    Player可以以step返回一个无副作用的决策
    或者以step_train返回一个可能有副作用（利用副作用更新行为方式）的决策
    其中比step多接受一个GameBoard对象
    look会在训练模式调用，会在传给对方决策同时（之前之后应该产生相同的
    行为）传给本方记录之类的。
    '''
    def setup(self):
        raise NotImplementedError
    def step(self, agg_wrap):
        raise NotImplementedError
    def step_train(self, agg_wrap, game_board):
        raise NotImplementedError
    def receive_score(self, score):
        raise NotImplementedError
    def look(self, agg_wrap):
        raise NotImplementedError
    def report(self):
        raise NotImplementedError
    def run_until_control_side_changed(self, agg_wrap):
        control_side = agg_wrap.control_side()
        
        while agg_wrap.control_side() == control_side:
            agg_wrap = self.step(agg_wrap)
        
        return agg_wrap
        
class NoLearningPlayer(Player):
    def setup(self):
        return
    def step_train(self, agg_wrap, game_board):
        return self.step(agg_wrap)
    def receive_score(self, score):
        return
    def look(self, agg_wrap):
        return
    def report(self):
        return
        
class RandomAI(NoLearningPlayer):
    def step(self, agg_wrap):
        return random.choice(agg_wrap.get_succ()).experiment()
        
class HumanPlayer(NoLearningPlayer):
    def __init__(self, exit_command = None):
        NoLearningPlayer.__init__(self)
        self.exit_command = {'exit','quit','e','q'} if exit_command == None else exit_command
    def step(self,agg_wrap):
        print(agg_wrap.agg_state.__str__())
        print('\n')
        succs = agg_wrap.get_succ()
        for i,succ in enumerate(succs):
            print('{id}. {text}'.format(id = i,text = succ.describe()['text']))
        inp = input('player>')
        if inp in self.exit_command:
            raise KeyboardInterrupt
        index = int(inp)
        return succs[index].experiment()
        
class UCTlikeAI(Player):
    def __init__(self, raw_history, priori, node_size = 1, explore_size = 10, is_look = False):
        self.raw_history = raw_history
        self.priori = priori
        self.node_size = node_size # 对一个点的实验次数
        self.explore_size = explore_size # 一个决定作出前的探索次数
        
        self.is_look = is_look
        
        self.raw_list = None
    def explore(self, agg_wrap, game_board):
        # 探索基本就是扩展一次"树"，这次扩展只使用一个胜负信息
        virtual_player = UCTlikeAI(self.raw_history, self.priori, node_size = self.node_size, explore_size = 0)
        game_board.subs_train(self,virtual_player)
    def step(self, agg_wrap):
        return UCT_choose_best(agg_wrap, self.raw_history, size = self.node_size, 
                               priori = self.priori)
    def step_train(self, agg_wrap, game_board):
        # train里会记录自己决策时的raw状态，look会记录（可以修改掉作为结构参数
        # 对方决策的状态
        self.raw_list.append(agg_wrap.to_raw())
        
        for i in range(self.explore_size):
            self.explore(agg_wrap, game_board)
        return self.step(agg_wrap)
    def setup(self):
        self.raw_list = []
    def receive_score(self, score):
        for raw in self.raw_list:
            if raw not in self.raw_history:
                self.raw_history[raw] = score.copy()
            else:
                for side_id,side_score in enumerate(score):
                    self.raw_history[raw][side_id] += side_score
        self.raw_list = None
    def look(self, agg_wrap):
        '''
        注意这个方法导致AI互博时可能权重加了两倍，此时让一方标为一方为train
        会导致不一样的行为（少了作为step方的探索行为）,所以应该把is_look关掉
        默认是关的
        '''
        if self.is_look:
            self.raw_list.append(agg_wrap.to_raw())
    def report(self):
        print("raw_history searched {}".format(len(self.raw_history)))
                
class GameBoard(object):
    def __init__(self, agg_wrap_base, side_0_player, side_1_player):
        self.agg_wrap_base = agg_wrap_base
        self.players = [side_0_player, side_1_player]
    def play(self):
        '''
        使用两个AI对局一盘
        '''
        agg_wrap = self.agg_wrap_base.copy()
        while not agg_wrap.is_end():
            control_side = agg_wrap.control_side()
            player = self.players[control_side]
            player.run_until_control_side_changed()
        return agg_wrap
    def _train_side_x(self, mode_list, n = 1, verbose = True):
        for i in range(n):
            self._play(mode_list)
            if verbose:
                print('AI played {}/{}'.format(i+1,n))
                for player in self.players:
                    player.report()
                # 因为这个对象不是面向raw_history的，所以不会汇报那些参数
    def train_side_0(self, **kwargs):
        self._train_side_x(['train','step'], **kwargs)
    def train_side_1(self, **kwargs):
        self._train_side_x(['step','train'], **kwargs)
    def train_both(self, **kwargs):
        self._train_side_x(['train','train'], **kwargs)
    def _play(self, mode_list):
        '''
        mode_list e.g
        ['step','train']
        '''
        agg_wrap = self.agg_wrap_base.copy()
        for i,mode in enumerate(mode_list):
            if mode == 'train':
                self.players[i].setup()
        
        while not agg_wrap.is_end():
            control_side = agg_wrap.control_side()
            if mode_list[1 - control_side] == 'train':
                self.players[1 - control_side].look(agg_wrap)
            if mode_list[control_side] == 'train':
                agg_wrap = self.players[control_side].step_train(agg_wrap,self)
            else:
                agg_wrap = self.players[control_side].step(agg_wrap)
                
        score = agg_wrap.end_score()
                
        for i,mode in enumerate(mode_list):
            if mode == 'train':
                self.players[i].receive_score(score)
                
        return agg_wrap
                
    def subs_player(self, player, agent_player):
        '''
        将player换成agent_player，生成一个新的GameBoard并返回
        '''
        index = self.players.index(player)
        if index == 0:
            game_board = GameBoard(self.agg_wrap_base, agent_player, self.players[1])
        elif index == 1:
            game_board = GameBoard(self.agg_wrap_base, self.players[0], agent_player)
        return game_board
    def subs_train(self, player, agent_player):
        game_board = self.subs_player(player, agent_player)
        mode_list = ['step','step']
        mode_list[self.players.index(player)] = 'train'
        game_board._play(mode_list)
                                    
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
                
def UCTlike_specify(agg_wrap_base, raw_history, side_control_map, size = 1, priori = 0.3):
    '''
    在这个函数下只有control_map没指定的side会使用raw_history，priori对应的
    UCT_choose_best进行决策。更新状态也只包含UCT控制的side的局面。
    side_control_map取值方式与run_game差不多，但可以取None值。此时用UCT决策并记录状态。
    '''
    agg_wrap = agg_wrap_base.copy()
    raw_list = []
    while not agg_wrap.is_end():
        
        external_control_func = side_control_map[agg_wrap.control_side()]
        
        if  external_control_func != None:
            # 虽然external_control_func一般来说应该是运行到控制权交换
            # 但只是走一步但从这个过程看也是允许的
            agg_wrap = external_control_func(agg_wrap)
        else:
        
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
        
def AI_play_self_specify(agg_wrap_base, raw_history, side_control_map, explore_size = 10, UCTlike_size = 1, UCTlike_priori = 0.5):
    '''
    AI将仅在side_control_map取None时使用raw_history决策。这么下完一盘
    伴随着raw_history更新的副作用。
    '''
    agg_wrap = agg_wrap_base.copy()
    while not agg_wrap.is_end():
        
        external_control_func = side_control_map[agg_wrap.control_side()]
        
        if external_control_func != None:
            agg_wrap = external_control_func(agg_wrap)
        else:
            for i in range(explore_size):
                UCTlike_specify(agg_wrap, raw_history, side_control_map, size = UCTlike_size, priori = UCTlike_priori)
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
            
def AI_play_self_n_specify(agg_wrap_base, raw_history, side_control_map, n = 10, verbose = True, **kwargs):
    for i in range(n):
        AI_play_self_specify(agg_wrap_base, raw_history, side_control_map, **kwargs)
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
run_game(agg_wrap,{0 : UCTlike_run_until_control_side_changed, 1 : player_run_until_control_side_changed})
'''

def raw_history_to_dataframe(raw_history, agg_wrap):
    import pandas
    mat = []
    for feature, result in raw_history.items():
        mat.append(feature + tuple(result))
    df = pandas.DataFrame(mat)
    df.columns = agg_wrap.feature_extractor.describe(agg_wrap.agg_state)['header'] + ('v1','v2')
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

def cross_analyse(agg_wrap, raw_history_list, priori_list, size = 100):
    '''
    以对应的raw_history与priori生成的决策函数进行上述交叉检验
    size指定一个特定组合的实验次数。
    对比
    random_run_until_control_side_changed
    UCTlike_choose1
    UCTlike_choose2
    三个决策函数在与自己对弈与分别对弈的3 * 3种情况中的A方胜率。
    胜率矩阵V_{ij}项表示i扮演A方而j扮演B方时的A方胜率，所以并不是对称的
    '''
    AI_list = [random_run_until_control_side_changed]
    for raw_history,priori in zip(raw_history_list,priori_list):
        UCTlike_choose = run_until_control_side_changed(lambda agg_wrap:UCT_choose_best(agg_wrap,raw_history = raw_history, priori = priori))
        AI_list.append(UCTlike_choose)
    #UCTlike_choose1 = run_until_control_side_changed(lambda agg_wrap:UCT_choose_best(agg_wrap,raw_history = raw_history1, priori = priori1))
    #UCTlike_choose2 = run_until_control_side_changed(lambda agg_wrap:UCT_choose_best(agg_wrap,raw_history = raw_history2, priori = priori2))
    ##run_game(agg_wrap,{'A':UCTlike_run_until_control_side_changed,'B':player_run_until_control_side_changed})
    
    #AI_list = [random_run_until_control_side_changed, UCTlike_choose1, UCTlike_choose2]
    mat = []
    for AI_A in AI_list:
        row = []
        for AI_B in AI_list:
            vs = 0
            for i in range(size):
                agg_wrap_end = run_game(agg_wrap,{0 : AI_A, 1 : AI_B})
                vs += agg_wrap_end.end_score()[0]
            row.append(vs/size)
        mat.append(row)
    return mat
    
'''
[[0.194, 0.681, 0.709], 
 [0.585, 0.605, 0.493], 
 [0.578, 0.696, 0.573]]
完全随机,priori=0.1,priori=0.3 100次训练三个AI的交叉矩阵 size=1000

很惭愧，光从矩阵上看，似乎只能得出训练之后的AI还不如随机乱走的AI强。

我本人测试感觉AI就会疯狂射击，根本不保留自己的mp，也往往不知道要进场援军
遇到结算也往往秘制选择移除自己单位.随机乱走时sideB可能会把自己单位移到A方
不能直接碰到的地方，然后就GG了。因为貌似AI只会对射。而对追击知之甚少。

纵向比较（内存药丸）

[[0.178, 0.681, 0.673], 
 [0.597, 0.569, 0.56], 
 [0.614, 0.497, 0.494]]
 
上面为完全随机 priori=0.3 训练100轮，200轮的结果 size = 1000
貌似更多训练对抗随机稍微强一点？然而对抗自己反而变弱？。。。意义不明，感觉
代码是不是写错了

[[0.192, 0.688, 0.684, 0.689],
 [0.592, 0.623, 0.645, 0.626],
 [0.588, 0.656, 0.627, 0.615],
 [0.601, 0.641, 0.625, 0.638]]


上面是完全随机，priori=0.1 训练100轮，200轮，300轮 size =1000的结果
感觉这差别完全可以由随机波动解释。

[[0.19, 0.681, 0.688], 
 [0.622, 0.541, 0.575], 
 [0.601, 0.559, 0.538]]
 
上面是完全随机,priori=0.1,0.3 训练200轮的交叉检验结果 size=1000
看上去说明还是priori=0.1更强一点？忘了

完全随机对抗特训：

先让AI以0方训练50轮（1方完全随机行动），倒过来再训练50轮结果为
[[0.186, 0.621], 
 [0.514, 0.171]]

虽然好像完全随机攻（扮演0方）效力有所下降，但有趣的是AI自我对抗的无能

再追加50轮自我对抗的结果

[[0.185, 0.565], 
 [0.629, 0.526]]

AI自我对抗能力部分恢复，有趣的是对抗完全随机攻的能力也上升了

接下来是单纯训练AI扮演1方100轮对抗完全随机0方看看效果
[[0.165, 0.68], 
 [0.525, 0.63]]
 
可以，貌似完全不符合预期。再加100轮
 
[[0.206, 0.639], 
 [0.514, 0.904]]
 
这。。所以再训练100轮呢（某种意义上倒是AI跑赢了随机）

[[0.179, 0.646], 
 [0.509, 0.831]]
 
可以，这很稳定。右下角那个明显是因为只把攻方当完全随机控制训练导致自己打自己都
不得行

'''
