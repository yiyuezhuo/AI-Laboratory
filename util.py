# -*- coding: utf-8 -*-
"""
Created on Fri Sep 23 08:22:04 2016

@author: yiyuezhuo
"""

import pickle

def pickle_load(path):
    with open(path,'rb') as f:
        obj = pickle.load(f)
    return obj
    
def pickle_dump(obj,path):
    with open(path,'wb') as f:
        obj = pickle.dump(obj,f)
