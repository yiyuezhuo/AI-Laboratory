# -*- coding: utf-8 -*-
"""
Created on Thu Sep 22 14:35:09 2016

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
        return self.agg_state.control_side_index()
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
    is_end 方法 识别是否终止
    end_score 方法 到底谁胜了
    control_side_index 按agg_state的control_side返回其在它side_list中的下标
    copy 要保证复制可变状态，不可变状态可以保持同一个引用
    '''
    def is_end(self):
        raise NotImplementedError
    def end_score(self):
        raise NotImplementedError
    def control_side_index(self):
        raise NotImplementedError
    def copy(self):
        raise NotImplementedError

        
class FeatureExtractor(object):
    '''
    特征提取器抽象类，提供无状态（起码对于算法来说，从实现看可以加点监视器）
    的extract方法从agg_state里提取像numpy.array一样的基础对象便于机械处理。
    describe则描述自己返回的向量各个分量的含义,用于交互接口，AI不可见
    '''
    def extract(self, agg_state):
        raise NotImplementedError
    def describe(self, agg_state):
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
