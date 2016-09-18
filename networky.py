# -*- coding: utf-8 -*-
"""
Created on Thu Sep 15 23:34:27 2016

@author: yiyuezhuo
"""

class Graph(object):
    '''
    这里提供一个类似networkx的Graph的简易版，懒得为这个导入networkx    
    '''
    def __init__(self):
        self.edge = {}
        self.node = {}
        self.adj  = {}
    def edges(self):
        l = []
        for source in self.edge.keys():
            for target in self.edge[source].keys():
                l.append((source, target))
        return l
    def nodes(self):
        return list(self.node.keys())
    def add_edge(self, source, target, attr_dict = None, **attr):
        if not source in self.node:
            self.add_node(source)
        if not target in self.node:
            self.add_node(target)
        if not source in self.edge:
            self.edge[source] = {}
        if not target in self.edge[source]:
            self.edge[source][target] = {}
        if attr_dict == None:
            attr_dict = {}
        self.edge[source][target].update(attr_dict)
        self.edge[source][target].update(attr)
        
        self.adj[source][target] = {}
        self.adj[target][source] = {}
    
    def add_node(self, n, attr_dict = None, **attr):
        attr_dict = {} if attr_dict == None else attr_dict
        if not n in self.node:
            self.node[n] = {}
            self.adj[n]  = {}
        self.node[n].update(attr_dict)
        self.node[n].update(attr)
    def neighbors(self, n):
        return list(self.adj[n])