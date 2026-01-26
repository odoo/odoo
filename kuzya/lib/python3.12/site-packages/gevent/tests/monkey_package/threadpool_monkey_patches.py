# -*- coding: utf-8 -*-
"""
This file runs ``gevent.monkey.patch_all()``.

It is intended to be used by ``python -m gevent.monkey <this file>``
to prove that monkey-patching twice doesn't have unfortunate sife effects (such as
breaking the threadpool).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
from gevent import monkey
from gevent import get_hub

monkey.patch_all(thread=False, sys=True)

def thread_is_greenlet():
    from gevent.thread import get_ident as gr_ident
    std_thread_mod = 'thread' if bytes is str else '_thread'
    thr_ident = monkey.get_original(std_thread_mod, 'get_ident')
    return thr_ident() == gr_ident()


is_greenlet = get_hub().threadpool.apply(thread_is_greenlet)
print(is_greenlet)
print(len(sys._current_frames()))
sys.stdout.flush()
sys.stderr.flush()
