# -*- coding: utf-8 -*-

def do_str_replace(string, type_check_out=True):
    if type_check_out:
        mapping_dict = {'-': '%2d', '_': '%5f', '.': '%2e', '!': '%21', '*': '%2a', '(': '%28', ')': '%29', '%2f': '%252f', '%3a': '%253a'}
    else:
        mapping_dict = {'-': '%2d', '_': '%5f', '.': '%2e', '!': '%21', '*': '%2a', '(': '%28', ')': '%29'}
    for key, val in mapping_dict.iteritems():
        string = string.replace(val, key)

    return string