# -*- coding: utf-8 -*-
from autojsdoc.parser.jsdoc import ParamDoc

"Lorem ipsum dolor sit amet, consectetur adipiscing elit."

def test_basic():
    d = ParamDoc("Lorem ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': 'Lorem',
        'type': '',
        'optional': False,
        'default': None,
        'doc': 'ipsum dolor sit amet, consectetur adipiscing elit.',
    }

    d = ParamDoc("{Lorem} ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': 'ipsum',
        'type': 'Lorem',
        'optional': False,
        'default': None,
        'doc': 'dolor sit amet, consectetur adipiscing elit.',
    }

def test_optional():
    d = ParamDoc("[Lorem] ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': 'Lorem',
        'type': '',
        'optional': True,
        'default': None,
        'doc': 'ipsum dolor sit amet, consectetur adipiscing elit.',
    }

    d = ParamDoc("[Lorem=42] ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': 'Lorem',
        'type': '',
        'optional': True,
        'default': "42",
        'doc': 'ipsum dolor sit amet, consectetur adipiscing elit.',
    }

    d = ParamDoc("{Lorem} [ipsum] dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': 'ipsum',
        'type': 'Lorem',
        'optional': True,
        'default': None,
        'doc': 'dolor sit amet, consectetur adipiscing elit.',
    }

    d = ParamDoc("{Lorem} [ipsum=42] dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': 'ipsum',
        'type': 'Lorem',
        'optional': True,
        'default': '42',
        'doc': 'dolor sit amet, consectetur adipiscing elit.',
    }

def test_returns():
    d = ParamDoc("{}  ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': '',
        'type': '',
        'optional': False,
        'default': None,
        'doc': 'ipsum dolor sit amet, consectetur adipiscing elit.',
    }
    d = ParamDoc("{Lorem}  ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d == {
        'name': '',
        'type': 'Lorem',
        'optional': False,
        'default': None,
        'doc': 'ipsum dolor sit amet, consectetur adipiscing elit.',
    }

def test_odd():
    d = ParamDoc("{jQuery} [$target] the node where content will be prepended").to_dict()
    assert d == {
        'name': '$target',
        'type': 'jQuery',
        'optional': True,
        'default': None,
        'doc': 'the node where content will be prepended',
    }

    d = ParamDoc("""{htmlString} [content] DOM element,
  array of elements, HTML string or jQuery object to prepend to $target""").to_dict()
    assert d == {
        'name': 'content',
        'type': 'htmlString',
        'optional': True,
        'default': None,
        'doc': "DOM element,\n  array of elements, HTML string or jQuery object to prepend to $target",
    }

    d = ParamDoc("{Boolean} [options.in_DOM] true if $target is in the DOM").to_dict()
    assert d == {
        'name': 'options.in_DOM',
        'type': 'Boolean',
        'optional': True,
        'default': None,
        'doc': 'true if $target is in the DOM',
    }

    d = ParamDoc("Lorem\n   ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d['doc'] == 'ipsum dolor sit amet, consectetur adipiscing elit.'

    d = ParamDoc("Lorem - ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d['doc'] == 'ipsum dolor sit amet, consectetur adipiscing elit.'

    d = ParamDoc("Lorem : ipsum dolor sit amet, consectetur adipiscing elit.").to_dict()
    assert d['doc'] == 'ipsum dolor sit amet, consectetur adipiscing elit.'
