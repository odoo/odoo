# -*- coding: utf-8 -*-

import imp
import sys

from pygments.style import Style
from pygments.token import *

# extracted from getbootstrap.com
class OdooStyle(Style):
    background_color = '#ffffcc'
    highlight_color = '#fcf8e3'
    styles = {
        Whitespace: '#BBB',
        Error: 'bg:#FAA #A00',

        Keyword: '#069',
        Keyword.Type: '#078',

        Name.Attribute: '#4F9FCF',
        Name.Builtin: '#366',
        Name.Class: '#0A8',
        Name.Constant: '#360',
        Name.Decorator: '#99F',
        Name.Entity: '#999',
        Name.Exception: '#C00',
        Name.Function: '#C0F',
        Name.Label: '#99F',
        Name.Namespace: '#0CF',
        Name.Tag: '#2F6F9F',
        Name.Variable: '#033',

        String: '#d44950',
        String.Backtick: '#C30',
        String.Char: '#C30',
        String.Doc: 'italic #C30',
        String.Double: '#C30',
        String.Escape: '#C30',
        String.Heredoc: '#C30',
        String.Interol: '#C30',
        String.Other: '#C30',
        String.Regex: '#3AA',
        String.Single: '#C30',
        String.Symbol: '#FC3',

        Number: '#F60',

        Operator: '#555',
        Operator.Word: '#000',

        Comment: '#999',
        Comment.Preproc: '#099',

        Generic.Deleted: 'bg:#FCC border:#c00',
        Generic.Emph: 'italic',
        Generic.Error: '#F00',
        Generic.Heading: '#030',
        Generic.Inserted: 'bg:#CFC border:#0C0',
        Generic.Output: '#AAA',
        Generic.Prompt: '#009',
        Generic.Strong: '',
        Generic.Subheading: '#030',
        Generic.Traceback: '#9C6',
    }


modname = 'pygments.styles.odoo'
m = imp.new_module(modname)
m.OdooStyle = OdooStyle
sys.modules[modname] = m
