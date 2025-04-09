import argparse
import importlib
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__,'../../../')))

import odoo.init
from odoo.modules.module import initialize_sys_path, get_modules, get_module_path
from odoo.netsvc import init_logger
from odoo.tools import config


def parse_args():
    parser = argparse.ArgumentParser(description='Run diff tests for Odoo')
    parser.add_argument('--addons-path', type=str, help='Specify addons path')
    parser.add_argument('--upgrade-path', type=str, help='Specify upgrade path')
    parser.add_argument('--diff-dir', type=str, help='Specify the absolute path for diff files')
    parser.add_argument('--gen-diff', action='store_true', help='Automatically generate git diff for debugging or local testing')
    parser.add_argument('--output', type=str, help='Specify the path for JSON results output')
    parser.add_argument('--test-tags', type=str, help='Specify test tags to run')
    return parser.parse_args()


if __name__ == '__main__':
    init_logger()
    args = parse_args()
    config._parse_config([
        '--addons-path', args.addons_path,
        '--upgrade-path', args.upgrade_path,
        '--test-enable',
        '--test-tags', args.test_tags,
    ])
    initialize_sys_path()

    if args.diff_dir and args.test_tags:
        if args.gen_diff:
            from odoo.tests.diffcase import generate_diff
            generate_diff(args.diff_dir)

        from odoo.tests.diffcase import DiffCase
        DiffCase.diff_dir = args.diff_dir

        from odoo.tests import loader  # noqa: PLC0415
        modules_paths = {module_name: get_module_path(module_name) for module_name in get_modules()}
        module_names = []
        for module_name in get_modules():
            if (module_path := modules_paths[module_name]) and os.path.isdir(os.path.join(module_path, 'tests_diff')):
                module_names.append(module_name)

        suite = loader.make_suite(module_names, 'no_install', mode='test_diff')
        if suite.countTestCases():
            test_results = loader.run_suite(suite, global_report={})

        if DiffCase.report:
            if args.output:
                os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
                with open(args.output, 'w') as f:
                    json.dump(DiffCase.report, f, indent=2)
            else:
                print(DiffCase.report)
