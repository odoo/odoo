import json
import logging
import os

from odoo.cli.command import Command
from odoo.modules.module import initialize_sys_path
from odoo.netsvc import init_logger
from odoo.tools import config

_logger = logging.getLogger(__name__)


class TestDiff(Command):
    """ Run the diff tests in the test_lint module """
    name = 'test_diff'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument('--diff-dir', type=str, required=True,
                               help='Specify the absolute path for git diff files. Diff files are .txt files whose first line is the absolute path of the file of the git project. And the rest of the file is the git diff of the file for the code.')
        self.parser.add_argument('--gen-diff', action='store_true',
                               help='Generate git diff files for git projects in the addons path based on their current branch name and save them in diff-dir')
        self.parser.add_argument('--output', type=str,
                               help='Specify the path for ruff-like JSON results output')
        self.parser.add_argument('--test-tags', type=str, dest="test_tags",
                               help='Specify test tags to filter tests.')

    def run(self, cmdargs):
        init_logger()
        parsed_args = self.parser.parse_args(args=cmdargs)
        config._parse_config([
            '--test-enable',
            '--test-tags', parsed_args.test_tags,
        ])
        initialize_sys_path()

        if parsed_args.gen_diff:
            from odoo.tests.diffcase import generate_diff  # noqa: PLC0415
            generate_diff(parsed_args.diff_dir)

        from odoo.tests.diffcase import DiffCase  # noqa: PLC0415
        DiffCase.diff_dir = parsed_args.diff_dir

        from odoo.tests import loader  # noqa: PLC0415
        suite = loader.make_suite(['test_lint'], 'test_diff')
        if suite.countTestCases():
            loader.run_suite(suite)

        if parsed_args.output:
            os.makedirs(os.path.dirname(os.path.abspath(parsed_args.output)), exist_ok=True)
            with open(parsed_args.output, 'w', encoding='utf-8') as f:
                json.dump(DiffCase.diagnostices, f, indent=2, default=lambda x: x.to_ruff())
        else:
            if DiffCase.diagnostices:
                for diagnostic in DiffCase.diagnostices:
                    _logger.warning(diagnostic.to_log())
            else:
                _logger.info('No issue found')
