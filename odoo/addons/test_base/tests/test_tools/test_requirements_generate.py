import sys
from pathlib import Path

from odoo.tests.common import BaseCase, no_retry

# generate.py/manifests.py live in setup/requirements/, outside the addons tree.
_REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(_REPO_ROOT / 'setup' / 'requirements'))

import generate  # noqa: E402
from manifests import select_modules  # noqa: E402

_ADDONS_PATH = [str(_REPO_ROOT / 'addons'), str(_REPO_ROOT / 'odoo' / 'addons')]


def _run_generate(precomputed_versions, python_versions=('all',), **kwargs):
    return generate.generate_requirements(
        _ADDONS_PATH, python_versions=list(python_versions), precomputed_versions=precomputed_versions, **kwargs
    )


@no_retry
class TestSelectModules(BaseCase):
    def setUp(self):
        super().setUp()
        self.manifests = {
            'base': {'depends': []},
            'web': {'depends': ['base']},
            'sale': {'depends': ['base', 'web']},
            'l10n_be': {'depends': ['base']},
            'l10n_be_sale': {'depends': ['l10n_be', 'sale']},
        }

    def test_no_patterns_selects_everything(self):
        self.assertEqual(select_modules(self.manifests, None), set(self.manifests))

    def test_wildcard_and_negate(self):
        selected = select_modules(self.manifests, ['*', '-l10n*'])
        self.assertEqual(selected, {'base', 'web', 'sale'})

    def test_selection_pulls_in_dependency_closure(self):
        # l10n_be_sale depends on l10n_be, so it must survive '-l10n_be'
        selected = select_modules(self.manifests, ['l10n_be_sale', '-l10n_be'])
        self.assertEqual(selected, {'base', 'web', 'sale', 'l10n_be', 'l10n_be_sale'})


@no_retry
class TestGenerateRequirements(BaseCase):
    def test_pin_and_group_by_python_version(self):
        output = _run_generate(
            modules=['auth_totp'],
            precomputed_versions={
                '3.12': {'python3-qrcode': '7.0.0'},
                '3.13': {'python3-qrcode': '7.5.0'},
                '3.14': {'python3-qrcode': '7.5.0'},
            },
        )
        self.assertIn("qrcode==7.0.0 ; python_version >= '3.12' and python_version < '3.13'\n", output)
        self.assertIn("qrcode==7.5.0 ; python_version >= '3.13'\n", output)
        self.assertNotIn("python_version >= '3.14'", output)

    def test_missing_from_distro_is_unpinned(self):
        output = _run_generate(
            modules=['auth_totp'],
            precomputed_versions={'3.12': {}, '3.13': {}, '3.14': {}},
        )
        self.assertIn('qrcode\n', output)

    def test_security_floor_only_applies_when_needed(self):
        output = _run_generate(
            modules=['base'],
            precomputed_versions={
                '3.12': {'python3-cryptography': '41.0.7'},
                '3.13': {'python3-cryptography': '43.0.0'},
                '3.14': {'python3-cryptography': '46.0.5'},
            },
        )
        self.assertIn(
            "cryptography==42.0.8 ; python_version >= '3.12' and python_version < '3.13'  # min 42.0.8 for security fixes\n",
            output,
        )
        self.assertIn("cryptography==43.0.0 ; python_version >= '3.13' and python_version < '3.14'\n", output)
        self.assertIn("cryptography==46.0.5 ; python_version >= '3.14'\n", output)
        self.assertIn('(security pins applied)', output.splitlines()[0])

    def test_ignore_security_disables_the_floor(self):
        output = _run_generate(
            modules=['base'],
            ignore_security=True,
            precomputed_versions={
                '3.12': {'python3-cryptography': '41.0.7'},
                '3.13': {'python3-cryptography': '43.0.0'},
                '3.14': {'python3-cryptography': '46.0.5'},
            },
        )
        self.assertIn("cryptography==41.0.7 ; python_version >= '3.12' and python_version < '3.13'\n", output)
        self.assertNotIn('42.0.8', output)
        self.assertIn('(security pins ignored)', output.splitlines()[0])

    def test_header_reports_no_security_pins_needed(self):
        # every declared floor is already satisfied: nothing should get bumped
        above_all_floors = {
            v: {'python3-h11': '99.0', 'python3-cryptography': '99.0', 'python3-openssl': '99.0'}
            for v in ('3.12', '3.13', '3.14')
        }
        output = _run_generate(modules=['base'], precomputed_versions=above_all_floors)
        self.assertIn('(no security pins needed)', output.splitlines()[0])

    def test_platform_filtering_default_excludes_windows_only(self):
        empty = {'3.12': {}, '3.13': {}, '3.14': {}}
        output = _run_generate(modules=['base'], precomputed_versions=empty)
        self.assertNotIn('pypiwin32', output)

        output = _run_generate(modules=['base'], platforms=['all'], precomputed_versions=empty)
        self.assertIn("pypiwin32 ; sys_platform == 'win32'\n", output)
