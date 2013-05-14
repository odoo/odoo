############################################################################
#   Copyright (C) 2005 by Reithinger GmbH
#   mreithinger@web.de
#
#   This file is part of faces.
#                                                                         
#   faces is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   faces is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
############################################################################

import observer
import os.path
import sys
import os.path

_call_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

def get_installation_path():
    try:
        if sys.frozen:
            path = _call_dir
        else:
            raise AttributeError()
    except AttributeError:
        path = os.path.abspath(observer.__file__)
        path = os.path.split(path)[0]
        
    path = os.path.normcase(path)
    return path


def get_resource_path():
    try:
        if sys.frozen:
            path = _call_dir
            path = os.path.join(path, "resources", "faces", "gui")
        else:
            raise AttributeError()
    except AttributeError:
        path = get_installation_path()
        path = os.path.join(path, "gui", "resources")

    path = os.path.normcase(path)
    return path


def get_template_path():
    try:
        if sys.frozen:
            path = _call_dir
            path = os.path.join(path, "resources", "faces", "templates")
        else:
            raise AttributeError()
    except AttributeError:
        path = get_installation_path()
        path = os.path.join(path, "templates")
        
    path = os.path.normcase(path)
    return path


def get_howtos_path():
    try:
        if sys.frozen:
            path = _call_dir
        else:
            raise AttributeError()
    except AttributeError:
        path = get_installation_path()

    path = os.path.join(path, "howtos")
    path = os.path.normcase(path)
    return path



def flatten(items):
    if isinstance(items, tuple):
        items = list(items)

    if not isinstance(items, list):
        yield items
    
    stack = [iter(items)]
    while stack:
        for item in stack[-1]:
            if isinstance(item, tuple):
                item = list(item)
            
            if isinstance(item, list):
                stack.append(iter(item))
                break
            yield item
        else:
            stack.pop()


def do_yield():
    pass


def progress_start(title, maximum, message=""):
    pass

def progress_update(value, message=""):
    pass

def progress_end():
    pass




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
