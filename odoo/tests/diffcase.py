import functools
import logging
import os
import re
import subprocess

from collections import defaultdict
from lxml import etree

from unidiff import PatchSet, PatchedFile

import odoo.addons

from .common import BaseCase
from odoo.tools import OrderedSet, config, lazy_classproperty
from odoo.tools.which import which

_logger = logging.getLogger(__name__)


class DiffFile:

    @lazy_classproperty
    def addons_paths(cls) -> list[str]:
        return [
            os.path.normpath(os.path.normcase(addons_path)) + os.sep
            for addons_path in odoo.addons.__path__
        ]

    def __init__(self, repo_path: str, patched_file: PatchedFile):

        self.path = os.path.join(repo_path, patched_file.path)  # /Users/username/project/odoo/odoo/addons/base/models/res_partner.py
        """ absolute path of the file """

        self.path_to_addons: str = self.extract_path_to_addons(self.path) or ''  # base/models/res_partner.py
        """ relative path of the file to one of the odoo addons path """

        self.module_name: str = self.path_to_addons.split(os.sep)[0]  # base
        """ module name of the file """

        self.path_to_module: str = self.path_to_addons[len(self.module_name) + len(os.sep):]  # models/res_partner.py
        """ relative path of the file to the odoo module's path """

        self.patched_file: PatchedFile = patched_file
        """ the patched file object from unidiff """

    @functools.cached_property
    def diff_linenos(self) -> set[int]:
        """ line numbers of new lines in the git diff of the file """
        # TBD:
        # use list[tuple[int, int]] instead of set[int] which only stores sorted [(start_lineno, end_lineno), ...]
        # and use bisect to check if the given line numbers are in the diff O(log(n))
        diff_linenos = set()
        for hunk in self.patched_file:
            for line in hunk:
                if line.is_added and line.target_line_no:
                    diff_linenos.add(line.target_line_no)
        return diff_linenos

    @classmethod
    def extract_path_to_addons(cls, abs_path: str) -> str | None:
        """ extract the relative path of the file to its odoo addons path """
        for addons_path in cls.addons_paths:
            if abs_path.startswith(addons_path) and len(abs_path) > len(addons_path):
                odoo_path = abs_path[len(addons_path):].strip(os.sep)
                return odoo_path
        return None

    def is_lineno_in_diff(self, start_lineno: int, end_lineno: int = 0) -> bool:
        """ check if the any given line in [start_lineno, end_lineno] inclusively is in the diff """
        if not end_lineno:
            end_lineno = start_lineno
        return any(line_no in self.diff_linenos for line_no in range(start_lineno, end_lineno + 1))


class DiagnosticKind:
    def __init__(self, name: str, body: str, suggestion: str):
        self.name: str = name
        """ The identifier of the diagnostic. """
        self.body: str = body
        """ The message body to display to the user, to explain the diagnostic. """
        self.suggestion: str = suggestion
        """ The message to display to the user, to explain the suggested fix. """

    def __call__(self, file: DiffFile, start: int | tuple[int, int], end: int | tuple[int, int] | None = None) -> 'DiagnosticMessage':
        return DiagnosticMessage(self, file, start, end)


class DiagnosticMessage:
    def __init__(self, kind: DiagnosticKind, file: DiffFile, start: int | tuple[int, int], end: int | tuple[int, int] | None = None):
        self.kind: DiagnosticKind = kind
        self.file: DiffFile = file
        self.start = (start, 0) if isinstance(start, int) else start
        self.end = (end, 0) if isinstance(end, int) else end if end else self.start

    def to_ruff(self) -> dict:
        # ruff like result
        result = {
            'code': self.kind.name,
            'location': {
                'row': self.start[0],
                'column': self.start[1] or 1,
            },
            'end_location': {
                'row': self.end[0],
                'column': self.end[1] or 1,
            },
            'filename': self.file.path,
            'message': self.kind.body,
        }
        if self.kind.suggestion:
            result['fix'] = {
                'message': self.kind.suggestion,
            }
        return result

    def to_log(self) -> str:
        return f'{self.file.path}:{self.start[0]} {self.kind.body}'


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
    _logger.info('Found %s repos', len(repo_paths))
    return list(repo_paths)


def get_base_version(repo_path: str) -> str:
    """ use git to get the base version of the current Odoo branch """
    try:
        branch_name = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            check=False,
            text=True,
            cwd=repo_path
        ).stdout.strip()
    except Exception as e:
        _logger.warning('Cannot get git base version for %s, %s', repo_path, e)
        return ''

    # master-xxx / saas-18.1-xxx / 18.0-xxx
    pattern = r'^(master|saas-\d+\.\d+|\d+\.\d+)(?:-|$)'
    match = re.match(pattern, branch_name)
    if match:
        return match.group(1)
    _logger.warning('Cannot get git base version of %s for %s', branch_name, repo_path)
    return ''


def generate_diff(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    for file in os.listdir(output_dir):
        if file.endswith('.txt'):
            os.remove(os.path.join(output_dir, file))

    repos = get_repos()
    if len({os.path.basename(repo) for repo in repos}) == len(repos):
        repo_names = {repo: os.path.basename(repo) for repo in repos}
    else:
        repo_names = {repo: repo.replace(os.sep, '.').strip('.') for repo in repos}

    for repo in repos:
        base_version = get_base_version(repo)
        if not base_version:
            continue
        diff_file_path = os.path.join(output_dir, f'{repo_names[repo]}_diff.txt')

        try:
            git = which('git')
            diff_command = [git, 'diff', '--unified=0', '--merge-base', base_version]

            with open(diff_file_path, 'w', encoding='utf-8') as f:
                f.write(f'{repo}\n')  # Write repo path as first line

                diff_output = subprocess.run(
                    diff_command,
                    capture_output=True,
                    check=False,
                    text=False,
                    cwd=repo
                ).stdout.decode(errors="replace")

                f.write(diff_output)

            _logger.info('Generated diff file for %s at %s', repo, diff_file_path)

        except Exception as e:
            _logger.warning('Cannot generate diff for %s:\n%s', repo, e)


class ElementInfo:
    def __init__(self, element: etree._Element):
        self.element = element

        self.start_tag_linenos = (0, 0)
        """(first_line_no_of_the_start_tag, last_line_no_of_the_start_tag)"""

        self.end_tag_lineno = 0
        """last_line_no_of_the_end_tag"""

        self.start_tag_in_diff = False
        """if the start tag is in the diff"""


class DiffCase(BaseCase):
    test_tags = {'no_install', 'standard', 'test_diff'}

    diff_files: dict[str, dict[str, DiffFile]] = defaultdict(dict)
    """ {file_extension: {abs_path: diff_file}} """

    diff_dir: str | None = None
    """ Path to a directory containing .txt diff files """

    diagnostices: list[DiagnosticMessage] = []

    @classmethod
    def parse_xml_file(cls, abs_path: str, diff_linenos: set[int] | None = None) -> tuple[etree.ElementTree, dict[etree._Element, ElementInfo]]:
        assert abs_path.endswith('.xml')
        if diff_linenos is None:
            diff_file = cls.diff_files['.xml'].get(abs_path)
            if not diff_file:
                return etree.ElementTree(None), {}
            diff_linenos = diff_file.diff_linenos

        with open(abs_path, 'rb') as fp:
            try:
                event_elements = list(etree.iterparse(fp, events=('start', 'end', 'comment', 'pi')))
            except etree.XMLSyntaxError:
                # usually because the xml is empty
                return etree.ElementTree(None), {}
        element_tree = event_elements[0][1].getroottree() if event_elements else etree.ElementTree(None)
        elements_info = {}

        previous_line = 1
        for event, element in event_elements:
            if event == 'start':
                element_info = elements_info[element] = ElementInfo(element)
                # element.sourceline is the line number of the last line of the start tag
                element_info.start_tag_linenos = (previous_line, element.sourceline)
                element_info.start_tag_in_diff = any(line in diff_linenos for line in range(previous_line, element.sourceline + 1))                
                previous_line = element.sourceline
                if element.text:
                    previous_line += element.text.count('\n')
            elif event == 'end':
                element_info = elements_info[element]
                # We assume the end tag is always on a single line.
                # Bad example that we don't support:
                #     </record
                #     >
                if element.tail:
                    previous_line += element.tail.count('\n')
                element_info.end_tag_lineno = previous_line
            else:  # 'comment', 'pi'
                # tricky case:
                # if the xml file starts/ends with a comment, the comment.getroottree()
                # will return the root tree. But the comment won't be in tree.iter()
                # so element_tree[_element] will get KeyError
                previous_line = element.sourceline
                if element.tail:
                    previous_line += element.tail.count('\n')

        return element_tree, elements_info

    @classmethod
    def setUpClass(cls):
        """Parse a custom diff file and initialize the diff_files dictionary"""
        if cls.diff_files:
            return
        cls.diff_files['.py']

        if cls.diff_dir is None:
            raise ValueError('DiffCase.diff_dir is not set')
        if not os.path.isdir(cls.diff_dir):
            raise ValueError(f"'{cls.diff_dir}' is not a directory")

        for filename in os.listdir(cls.diff_dir):
            if not filename.endswith('.txt'):
                continue

            file_path = os.path.join(cls.diff_dir, filename)
            _logger.info('Processing diff file: %s', file_path)

            try:
                with open(file_path, encoding='utf-8') as f:
                    repo_path = f.readline().strip()
                    if not os.path.isdir(repo_path):
                        _logger.warning('Invalid repository path: %s', repo_path)
                        continue

                    # Read the rest of the file content for diff
                    diff_content = f.read()

                    # Parse diff using unidiff
                    if PatchSet is None:
                        raise ImportError('unidiff is not installed')
                    patch_set = PatchSet.from_string(diff_content)

                    # Process each patched file
                    for patched_file in patch_set:
                        abs_path = os.path.join(repo_path, patched_file.path)
                        diff_file = DiffFile(repo_path, patched_file)

                        # Add line numbers from the diff
                        for hunk in patched_file:
                            for line in hunk:
                                if line.is_added and line.target_line_no:
                                    diff_file.diff_linenos.add(line.target_line_no)

                        # Store the diff file based on file extension
                        ext = os.path.splitext(abs_path)[1].lower()
                        cls.diff_files[ext][abs_path] = diff_file

            except Exception as e:
                _logger.error('Error processing diff file %s: %s', file_path, e)
