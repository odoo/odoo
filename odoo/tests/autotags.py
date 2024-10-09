import re
import urllib.error
import urllib.request
from typing import Callable

import pytest

SKIP_TAGGED = pytest.mark.skip(reason="tagged on runbot")

TagPredicate = pytest.StashKey[Callable[[pytest.Item], None]]()
tag_re = re.compile(r"""
    # runbot automatically prepends `-` to disable
    -
    (:?/(?P<module>\w+))?
    (:?:(?P<class>\w+))?
    (:?\.(?P<method>\w+))?
""" , re.VERBOSE)


def pytest_configure(config: pytest.Config):
    if config.getoption('--help'):
        return

    try:
        r = urllib.request.urlopen("https://runbot.odoo.com/runbot/auto-tags", timeout=1)
    except urllib.error.URLError:
        return

    # ignore match failure as technically the runbot *could* use an actual tag(ged)
    predicates = []
    for m in filter(None, map(tag_re.fullmatch, r.read().decode().split(','))):
        pred = []
        if n := m['method']:
            pred.append(f'fn.__name__ == {n!r}')
        if n := m['class']:
            n += '.'
            pred.append(f'fn.__qualname__.startswith({n!r})')
        if n := m['module']:
            n = f'odoo.addons.{n}.'
            pred.append(f'fn.__module__.startswith({n!r})')

        if pred:
            predicates.append(" and ".join(pred))

    if predicates:
        tagged = eval("lambda fn: " + " or ".join(f"({p})" for p in predicates), {'__builtins__': {}}, {})
    else:
        tagged = lambda _: False

    config.stash[TagPredicate] = tagged


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    p = config.stash[TagPredicate]
    for item in items:
        # all items here seem to be function but might as well check
        if isinstance(item, pytest.Function) and p(item.function):
            item.add_marker(SKIP_TAGGED)
