
try:
    # Do this before the patch to be sure we clean
    # things up properly if the order is wrong.
    import selectors
except ImportError:
    import selectors2 as selectors

from gevent.monkey import patch_all
import gevent.testing as greentest

patch_all()

from gevent.selectors import DefaultSelector
from gevent.selectors import GeventSelector
from gevent.tests.test__selectors import SelectorTestMixin

class TestSelectors(SelectorTestMixin, greentest.TestCase):

    @greentest.skipOnWindows(
        "SelectSelector._select is a normal function on Windows"
    )
    def test_selectors_select_is_patched(self):
        # https://github.com/gevent/gevent/issues/835
        _select = selectors.SelectSelector._select
        self.assertIn('_gevent_monkey', dir(_select))

    def test_default(self):
        # Depending on the order of imports, gevent.select.poll may be defined but
        # selectors.PollSelector may not be defined.
        # https://github.com/gevent/gevent/issues/1466
        self.assertIs(DefaultSelector, GeventSelector)
        self.assertIs(selectors.DefaultSelector, GeventSelector)

    def test_import_selectors(self):
        # selectors can always be imported once monkey-patched. On Python 2,
        # this is an alias for gevent.selectors.
        __import__('selectors')

    def _make_test(name, kind): # pylint:disable=no-self-argument
        if kind is None:
            def m(self):
                self.skipTest(name + ' is not defined')
        else:
            def m(self, k=kind):
                with k() as sel:
                    self._check_selector(sel)
        m.__name__ = 'test_selector_' + name
        return m

    SelKind = SelKindName = None
    for SelKindName in (
            # The subclass hierarchy changes between versions, and is
            # complex (e.g, BaseSelector <- BaseSelectorImpl <-
            # _PollLikSelector <- PollSelector) so its easier to check against
            # names.
            'KqueueSelector',
            'EpollSelector',
            'DevpollSelector',
            'PollSelector',
            'SelectSelector',
            GeventSelector,
    ):
        if not isinstance(SelKindName, type):
            SelKind = getattr(selectors, SelKindName, None)
        else:
            SelKind = SelKindName
            SelKindName = SelKind.__name__
        m = _make_test(SelKindName, SelKind) # pylint:disable=too-many-function-args
        locals()[m.__name__] = m

    del SelKind
    del SelKindName
    del _make_test



if __name__ == '__main__':
    greentest.main()
