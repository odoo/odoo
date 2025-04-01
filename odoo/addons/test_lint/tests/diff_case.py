import logging
import os
import re
import subprocess

from collections import defaultdict
from lxml import etree
from typing import Generator, Literal

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
        """ base version of the git branch """

        self.repo_path: str = repo_path and os.path.normpath(os.path.normcase(repo_path))  # /Users/username/project/odoo
        """ absolute path of the git repo """

        self.git_path: str = git_path and os.path.normpath(os.path.normcase(git_path))  # odoo/addons/base/models/res_partner.py
        """ relative path of the file to the git repo_path """

        self.abs_path = os.path.join(self.repo_path, self.git_path)  # /Users/username/project/odoo/odoo/addons/base/models/res_partner.py
        """ absolute path of the file """

        self.odoo_path: str = self.parse_odoo_path(self.abs_path)  # base/models/res_partner.py
        """ odoo path of the file """

        self.module_name: str = self.odoo_path.split(os.sep)[0]  # base
        """ module name of the file """

        self.module_path: str = self.odoo_path[len(self.module_name) + len(os.sep):]  # models/res_partner.py
        """ relative path of the file to the odoo module's path """

        self.diff_linenos: set[int] = set()
        """ line numbers of new lines in the git diff of the file """

    @classmethod
    def parse_odoo_path(cls, abs_path: str) -> str:
        """ parse the odoo path from the given absolute path """
        for addons_path in cls.addons_paths:
            if abs_path.startswith(addons_path) and len(abs_path) > len(addons_path):
                odoo_path = abs_path[len(addons_path):].strip(os.sep)
                return odoo_path
        return ''


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
    filter_cmd = ['--', *filter] if filter else []
    p1 = subprocess.Popen([which("git"), "diff", "--unified=0", base_version] + filter_cmd, stdout=subprocess.PIPE, cwd=repo_path)
    p2 = subprocess.Popen([which("grep"), "-E", "^(@@|diff --git)"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
    file_regex = re.compile(r'^diff --git a/[^\s]+ b/(?P<git_path>[^\s]+)')
    line_regex = re.compile(r'^@@ -[0-9,]+ \+(?P<start>[0-9]+),?(?P<count>[0-9]*) @@')
    current_file: FileInfo
    diff_linenos: dict[str, FileInfo] = {}
    for diff in p2.communicate()[0].split('\n'):
        if diff.startswith('diff --git'):
            match = file_regex.match(diff)
            assert match
            current_file = FileInfo(repo_path=repo_path, git_path=match.group('git_path'), base_version=base_version)
            diff_linenos[current_file.abs_path] = current_file
        elif diff.startswith('@@'):
            match = line_regex.match(diff)
            assert match
            start = int(match.group('start'))
            count = int(match.group('count')) if match.group('count') else 1
            current_file.diff_linenos |= set(range(start, start + count))
    return diff_linenos


class DiffCase(BaseCase):
    diff_linenos: dict[Literal['python', 'xml'], dict[str, FileInfo]] = defaultdict(dict)
    """ {file_category: {abs_path: file_info}} """
    for repo in get_repos():
        if base_version := get_base_version(repo):
            diff_linenos['python'].update(get_diff_linenos(repo, base_version, ["*.py"]))
            diff_linenos['xml'].update(get_diff_linenos(repo, base_version, ["*.xml"]))

    @classmethod
    def yield_xml_diff_elements(cls, abs_path: str, diff_linenos: set[int] | None = None) -> Generator[etree._Element, None, None]:
        assert abs_path.endswith('.xml')
        if diff_linenos is None:
            file_info = cls.diff_linenos['xml'].get(abs_path)
            if not file_info:
                return
            diff_linenos = file_info.diff_linenos
        _logger.info(f"Checking {abs_path}")
        with open(abs_path, 'rb') as fp:
            previous_line = 1
            # `list` the iterpase result to promise each element has all the attributes
            for event, element in list(etree.iterparse(fp, events=("start", "end", "comment", "pi"))):
                if event == "start":
                    # element.sourceline is the line number of the last line of the start tag
                    if any(line in diff_linenos for line in range(previous_line, element.sourceline + 1)):
                        yield element
                    previous_line = element.sourceline
                    if element.text:
                        previous_line += element.text.count('\n')
                elif event == "end":
                    # We assume the end tag is always on a single line.
                    # Bad example that we don't support:
                    #     </record
                    #     >
                    if element.tail:
                        previous_line += element.tail.count('\n')
                else:  # "comment", "pi"
                    previous_line = element.sourceline
                    if element.tail:
                        previous_line += element.tail.count('\n')
