import argparse
import importlib
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__,'../../../')))

import odoo.init
from odoo.modules.module import initialize_sys_path
from odoo.netsvc import init_logger
from odoo.tools import config


def parse_args():
    parser = argparse.ArgumentParser(description='Run diff tests for Odoo')
    parser.add_argument('--addons-path', type=str, help='Specify addons path')
    parser.add_argument('--diff-dir', type=str, help='Specify the absolute path for diff files')
    parser.add_argument('--test-modules', type=str, help='Specify tests to run in format: module')
    parser.add_argument('--gen-diff', action='store_true', help='Automatically generate git diff for debugging or local testing')
    parser.add_argument('--output', type=str, help='Specify the path for JSON results output')
    return parser.parse_args()


if __name__ == '__main__':
    init_logger()
    args = parse_args()
    config._parse_config(['--addons-path', args.addons_path, '--test-enable'])
    initialize_sys_path()

    if args.diff_dir and args.test_modules:
        if args.gen_diff:
            from odoo.tests.diffcase import generate_diff
            generate_diff(args.diff_dir)

        modules = args.test_modules.split(',')
        mdoules = [m.strip() for m in modules]
        for m in mdoules:
            module = f'odoo.addons.{m}.tests_diff'
            importlib.import_module(module)

        from odoo.tests.diffcase import DiffCase
        DiffCase.init_diff(args.diff_dir)
        DiffCase.run_all_tests()
        if DiffCase.report:
            if args.output:
                os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
                with open(args.output, 'w') as f:
                    json.dump(DiffCase.report, f, indent=2)
            else:
                print(DiffCase.report)
