# coding=utf-8
# -*- encoding: utf-8 -*-

import glob
import itertools
import json
import operator
import os

from mako.template import Template
from openerp.modules import module

from .main import module_topological_sort
from .. import http, nonliterals

NOMODULE_TEMPLATE = Template(u"""<!DOCTYPE html>
<html>
    <head>
        <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <title>OpenERP Testing</title>
    </head>
    <body>
        <form action="/web/tests" method="GET">
            <button name="mod" value="*">Run all tests</button>
            <ul>
            % for name, module in modules:
                <li>${name} <button name="mod" value="${module}">
                    Run Tests</button></li>
            % endfor
            </ul>
        </form>
    </body>
</html>
""")
NOTFOUND = Template(u"""
<p>Unable to find the module [${module}], please check that the module
   name is correct and the module is on OpenERP's path.</p>
<a href="/web/tests">&lt;&lt; Back to tests</a>
""")
TESTING = Template(u"""<!DOCTYPE html>
<html style="height: 100%">
<%def name="to_path(module, p)">/${module}/${p}</%def>
<head>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title>OpenERP Web Tests</title>
    <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>

    <link rel="stylesheet" href="/web/static/lib/qunit/qunit.css">
    <script src="/web/static/lib/qunit/qunit.js"></script>

    <script type="text/javascript">
        var oe_db_info = ${db_info};
        // List of modules, each module is preceded by its dependencies
        var oe_all_dependencies = ${dependencies};
        QUnit.config.testTimeout = 5 * 60 * 1000;
    </script>
</head>
<body id="oe" class="openerp">
    <div id="qunit"></div>
    <div id="qunit-fixture"></div>
</body>
% for module, jss, tests, templates in files:
    % for js in jss:
        <script src="${to_path(module, js)}"></script>
    % endfor
    % if tests or templates:
    <script>
        openerp.testing.current_module = "${module}";
        % for template in templates:
        openerp.testing.add_template("${to_path(module, template)}");
        % endfor
    </script>
    % endif
    % if tests:
        % for test in tests:
            <script type="text/javascript" src="${to_path(module, test)}"></script>
        % endfor
    % endif
% endfor
</html>
""")

nonliteral_test_contexts = [
    "{'default_opportunity_id': active_id, 'default_duration': 1.0, 'lng': lang}",
]
nonliteral_test_domains = [
    "['|', '&', ('date', '!=', False), ('date', '<=', time.strftime('%Y-%m-%d')), ('is_overdue_quantity', '=', True)]",
    "[('company_id', '=', context.get('company_id',False))]",
    "[('year','=',time.strftime('%Y'))]",
    "[('state','=','draft'),('date_order','<',time.strftime('%Y-%m-%d %H:%M:%S'))]",
    "[('state','!=','cancel'),('opening_date','>',datetime.date.today().strftime('%Y-%m-%d'))]",
    "[('type','=','in'),('day','<=', time.strftime('%Y-%m-%d')),('day','>',(datetime.date.today()-datetime.timedelta(days=15)).strftime('%Y-%m-%d'))]",
]

class TestRunnerController(http.Controller):
    _cp_path = '/web/tests'

    @http.httprequest
    def index(self, req, mod=None, **kwargs):
        ms = module.get_modules()
        manifests = dict(
            (name, desc)
            for name, desc in zip(ms, map(self.load_manifest, ms))
            if desc # remove not-actually-openerp-modules
        )

        if not mod:
            return NOMODULE_TEMPLATE.render(modules=(
                (manifest['name'], name)
                for name, manifest in manifests.iteritems()
                if any(testfile.endswith('.js')
                       for testfile in manifest['test'])
            ))
        sorted_mods = module_topological_sort(dict(
            (name, manifest.get('depends', []))
            for name, manifest in manifests.iteritems()
        ))
        # to_load and to_test should be zippable lists of the same length.
        # A falsy value in to_test indicate nothing to test at that index (just
        # load the corresponding part of to_load)
        to_test = sorted_mods
        if mod != '*':
            if mod not in manifests:
                return req.not_found(NOTFOUND.render(module=mod))
            idx = sorted_mods.index(mod)
            to_test = [None] * len(sorted_mods)
            to_test[idx] = mod

        tests_candicates = [
            filter(lambda path: path.endswith('.js'),
                   manifests[mod]['test'] if mod else [])
            for mod in to_test]
        # remove trailing test-less modules
        tests = reversed(list(
            itertools.dropwhile(
                operator.not_,
                reversed(tests_candicates))))

        files = [
            (mod, manifests[mod]['js'], tests, manifests[mod]['qweb'])
            for mod, tests in itertools.izip(sorted_mods, tests)
        ]

        # if all three db_info parameters are present, send them to the page
        db_info = dict((k, v) for k, v in kwargs.iteritems()
                       if k in ['source', 'supadmin', 'password'])
        if len(db_info) != 3:
            db_info = None

        return TESTING.render(files=files, dependencies=json.dumps(
            [name for name in sorted_mods
             if module.get_module_resource(name, 'static')
             if manifests[name]['js']]), db_info=json.dumps(db_info))

    @http.jsonrequest
    def load_context(self, req, index):
        return nonliterals.Context(req.session, nonliteral_test_contexts[index])
    @http.jsonrequest
    def load_domain(self, req, index):
        return nonliterals.Domain(req.session, nonliteral_test_domains[index])

    def load_manifest(self, name):
        manifest = module.load_information_from_description_file(name)
        if manifest:
            path = module.get_module_path(name)
            manifest['js'] = list(
                self.expand_patterns(path, manifest.get('js', [])))
            manifest['test'] = list(
                self.expand_patterns(path, manifest.get('test', [])))
            manifest['qweb'] = list(
                self.expand_patterns(path, manifest.get('qweb', [])))
        return manifest

    def expand_patterns(self, root, patterns):
        for pattern in patterns:
            normalized_pattern = os.path.normpath(os.path.join(root, pattern))
            for path in glob.glob(normalized_pattern):
                # replace OS path separators (from join & normpath) by URI ones
                yield path[len(root):].replace(os.path.sep, '/')
