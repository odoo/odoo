import logging
import os
import re
import subprocess

from collections import defaultdict
from lxml import etree
from typing import Generator

import odoo.addons

from odoo.tests import BaseCase
from odoo.tools import OrderedSet, config
from odoo.tools.which import which

_logger = logging.getLogger(__name__)


class FileInfo:
    root_path = os.path.abspath(config.root_path)
    addons_paths = [
        os.path.normpath(os.path.normcase(addons_path)) + os.sep
        for addons_path in odoo.addons.__path__
    ]

    def __init__(self, /, *, repo_path: str = '', git_path: str = '', base_version: str = ''):
        self.base_version: str = base_version
        self.repo_path: str = repo_path and os.path.normpath(os.path.normcase(repo_path))  # /Users/username/project/odoo
        self.git_path: str = git_path and os.path.normpath(os.path.normcase(git_path))  # odoo/addons/base/models/res_partner.py
        self.abs_path = os.path.join(self.repo_path, self.git_path)  # /Users/username/project/odoo/odoo/addons/base/models/res_partner.py
        self.odoo_path: str = self.parse_odoo_path(self.abs_path) or ''  # base/models/res_partner.py
        self.module_name: str = self.odoo_path.split(os.sep)[0]  # base
        self.module_path: str = self.odoo_path[len(self.module_name) + len(os.sep):]  # models/res_partner.py
        self.diff_lines: set[int] = set()

    @classmethod
    def parse_odoo_path(cls, abs_path: str) -> str | None:
        """ parse the odoo path from the given absolute path """
        for addons_path in cls.addons_paths:
            if abs_path.startswith(addons_path) and len(abs_path) > len(addons_path):
                odoo_path = abs_path[len(addons_path):].strip(os.sep)
                return odoo_path
        return None


def get_repos() -> list[str]:
    """ get all git repos in the given path """
    repo_paths = OrderedSet()
    for addon_path in config['addons_path']:
        try:
            git = which('git')
            repo_path = subprocess.run(
                [git, 'rev-parse', '--show-toplevel'],
                capture_output=True,
                check=False,
                text=True,
                cwd=addon_path
            ).stdout.strip()
            if repo_path:
                repo_paths.add(repo_path)
        except Exception as e:
            continue
    _logger.info(f"Found {len(repo_paths)} repos")
    return list(repo_paths)


def get_base_version(repo_path: str) -> str:
    """ use git to get the base version of the current Odoo branch """
    try:
        branch_name = subprocess.run(
            ['git', "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
            cwd=repo_path
        ).stdout.strip()
    except Exception as e:
        return ''

    # master-xxx / saas-18.1-xxx / 18.0-xxx
    pattern = r'^(master|saas-\d+\.\d+|\d+\.\d+)(?:-|$)'
    match = re.match(pattern, branch_name)
    if match:
        return match.group(1)
    return ''


def get_diff_linenos(repo_path: str, base_version: str, filter: list[str] | None = None) -> dict[str, FileInfo]:
    """ get the lines of the diff for files in the given repo
    
    :param repo_path: the absolute path of the git repo
    :param base_version: the base version to get the diff for
    :param filter: the files to get the diff for

    :return: the lines of the diff all files
    """
    git = which('git')
    filter_cmd = ['--', *filter] if filter else []
    p1 = subprocess.Popen([git, "diff", "--unified=0", base_version] + filter_cmd, stdout=subprocess.PIPE, cwd=repo_path)
    p2 = subprocess.Popen(["grep", "-E", "^(@@|diff --git)"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
    file_regex = re.compile(r'^diff --git a/[^\s]+ b/(?P<git_path>[^\s]+)')
    line_regex = re.compile(r'^@@ -[0-9,]+ \+(?P<start>[0-9]+),?(?P<count>[0-9]*) @@')
    current_file: FileInfo
    file_diffs: dict[str, FileInfo] = {}
    for diff in p2.communicate()[0].split('\n'):
        if diff.startswith('diff --git'):
            match = file_regex.match(diff)
            assert match
            current_file = FileInfo(repo_path=repo_path, git_path=match.group('git_path'), base_version=base_version)
            file_diffs[current_file.abs_path] = current_file
        elif diff.startswith('@@'):
            match = line_regex.match(diff)
            assert match
            start = int(match.group('start'))
            count = int(match.group('count')) if match.group('count') else 1
            current_file.diff_lines |= set(range(start, start + count))
    return file_diffs


class DiffCase(BaseCase):
    diff_linenos: dict[str, dict[str, FileInfo]] = defaultdict(dict)
    """ {file_category: {abs_path: file_info}}"""
    for repo in get_repos():
        if base_version := get_base_version(repo):
            diff_linenos['python'].update(get_diff_linenos(repo, base_version, ["*.py"]))
            diff_linenos['xml'].update(get_diff_linenos(repo, base_version, ["*.xml"]))

    @classmethod
    def yield_xml_diff_elements(cls, abs_path: str) -> Generator[etree._Element, None, None]:
        assert abs_path.endswith('.xml')
        file_info = cls.diff_linenos['xml'].get(abs_path)
        if not file_info:
            return
        _logger.info(f"Checking {abs_path}")
        with open(abs_path, 'rb') as fp:
            previous_tag_line = 0
            for event, element in etree.iterparse(fp, events=("start", "end")):
                if event == "start":
                    # elemen.source line is the last line of the tag declaration
                    # start_line should be the first line of the tag declaration
                    # the below is an estimation with one corner case
                    #
                    # ...  > <field ref='xxx'
                    # ... />
                    # 
                    # where
                    # 1. the end of the previous tag and the start line of the current tag are in the same line
                    # 2. the current tag is multiline
                    # 3. only the start line of the current tag is modified
                    # usually in a easy to read xml, if a start tag follows the prvious tag in the same line,
                    # its closing tag should be in the same line. So the corner case is acceptable.
                    start_line = min(element.sourceline, previous_tag_line + 1)
                    if not any(line in file_info.diff_lines for line in range(start_line, element.sourceline + 1)):
                        continue
                    yield element
                    previous_tag_line = element.sourceline
                elif event == "end":
                    previous_tag_line = element.sourceline
                    element.clear()
