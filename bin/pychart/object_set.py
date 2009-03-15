#
# Copyright (C) 2000-2005 by Yasushi Saito (yasushi.saito@gmail.com)
# 
# Jockey is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# Jockey is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
class T(object):
    def __init__(self, *objs):
        self.__objs = list(objs)
    def add(self, *objs):
        self.__objs.extend(objs)
    def add_objects(self, objs):
        self.__objs.extend(objs)
    def iterate(self):
        return Iterator(self)
    def list(self):
        return self.__objs
    def __getitem__(self, idx):
        return self.__objs[idx]
    def nth(self, idx):
        return self.__objs[idx]
    
class Iterator(object):
    def __init__(self, set_):
        self.__set = set_
        self.__idx = 0
    def reset(self):
        self.__idx = 0
    def next(self):
        val = self.__set.nth(self.__idx)
        self.__idx += 1
        if self.__idx >= len(self.__set.list()):
            self.__idx = 0
        return val

    
