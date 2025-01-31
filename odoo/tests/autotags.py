import re
import urllib.error
import urllib.request
from typing import Callable

import pytest

SKIP_TAGGED = pytest.mark.skip(reason="tagged on runbot")

Tags = pytest.StashKey[str]()
TagPredicate = pytest.StashKey[Callable[[pytest.Item], None]]()
tag_re = re.compile(r"""
    # runbot automatically prepends `-` to disable
    -
    (:?/(?P<module>\w+))?
    (:?:(?P<class>\w+))?
    (:?\.(?P<method>\w+))?
""" , re.VERBOSE)

pytest_plugins = ["odoo.tests.pytest"]


def pytest_configure(config: pytest.Config):
    if config.getoption('--help'):
        return

    tagged = lambda _: False
    config.stash[Tags] = ''
    try:
        # TODO: have runbot to provide more useful cache headers so we don't
        #       need to read & parse the body if the version we have is still
        #       valid?
        r = urllib.request.urlopen("https://runbot.odoo.com/runbot/auto-tags", timeout=1)
    except TimeoutError:
        # FIXME: cache `predicates`, and get the previous version from the cache if none can be retrieved?
        pass
    else:
        # ignore match failure as technically the runbot *could* use an actual tag(ged)
        predicates = []
        tags = []
        for m in filter(None, map(tag_re.fullmatch, r.read().decode().strip().split(','))):
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
                tags.append("".join(filter(None, [
                    m['module'] and f"odoo/addons/{m['module']}/*",
                    m['class'] and f"::{m['class']}",
                    m['method'] and f"::{m['method']}",
                ])))
        if tags:
            config.stash[Tags] = f"not ({' or '.join(tags)})"
        if predicates:
            tagged = eval("lambda fn: " + " or ".join(f"({p})" for p in predicates), {'__builtins__': {}}, {})

    config.stash[TagPredicate] = tagged


# tryfist because pytest displays these in reverse loading order by default,
# so the last hook to run has its contents displayed first
@pytest.hookimpl(tryfirst=True)
def pytest_report_header(config: pytest.Config):
    return f"autotags: {config.stash[Tags]}"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    p = config.stash[TagPredicate]
    for item in items:
        # all items here seem to be function but might as well check
        if isinstance(item, pytest.Function) and p(item.function):
            item.add_marker(SKIP_TAGGED)
