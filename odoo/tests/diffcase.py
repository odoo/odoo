import logging
import os
import re
import subprocess

from collections import defaultdict
from lxml import etree
from typing import Any, Generator

from unidiff import PatchSet, PatchedFile

import odoo.addons

from .common import BaseCase
from odoo.tools import OrderedSet, config, lazy_classproperty, lazy_property
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

    @lazy_property
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
        """ check if the given lines [start_lineno, end_lineno] inclusively are in the diff """
        if not end_lineno:
            end_lineno = start_lineno
        return any(line_no in self.diff_linenos for line_no in range(start_lineno, end_lineno + 1))


class Element:
    __slots__ = ('start_tag_linenos', 'end_tag_lineno', 'start_tag_in_diff', '_element')

    def __init__(self, element: etree._Element):
        self._element: etree._Element = element
        self.start_tag_linenos: tuple[int, int] = (0, 0)
        self.end_tag_lineno: int = 0
        self.start_tag_in_diff: bool = False

    def __getattr__(self, name: str) -> Any:
        if name in self.__slots__:
            return getattr(self, name)
        return getattr(self._element, name)


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

    def to_ruff_json(self) -> dict:
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
                'message':self.kind.suggestion,
            }
        return result


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
    _logger.info(f'Found {len(repo_paths)} repos')
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
        _logger.warning(f'Cannot get git base version for {repo_path}: {e}')
        return ''

    # master-xxx / saas-18.1-xxx / 18.0-xxx
    pattern = r'^(master|saas-\d+\.\d+|\d+\.\d+)(?:-|$)'
    match = re.match(pattern, branch_name)
    if match:
        return match.group(1)
    _logger.warning(f'Cannot get git base version of {branch_name} for {repo_path}')
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

            with open(diff_file_path, 'w') as f:
                f.write(f'{repo}\n')  # Write repo path as first line

                diff_output = subprocess.run(
                    diff_command,
                    capture_output=True,
                    check=False,
                    text=True,
                    cwd=repo
                ).stdout
                
                f.write(diff_output)

            _logger.info(f'Generated diff file for {repo} at {diff_file_path}')

        except Exception as e:
            _logger.warning(f'Cannot generate diff for {repo}:\n{e}')


class DiffCase(BaseCase):
    test_tags = {'no_install', 'standard'}

    diff_files: dict[str, dict[str, DiffFile]] = defaultdict(dict)
    """ {file_extension: {abs_path: diff_file}} """

    diff_dir: str | None = None
    """ Path to a directory containing .txt diff files """

    diagnostices: list[DiagnosticMessage] = []

    @classmethod
    def get_xml_elements(cls, abs_path: str, diff_linenos: set[int] | None = None) -> list[Element]:
        assert abs_path.endswith('.xml')
        if diff_linenos is None:
            diff_file = cls.diff_files['.xml'].get(abs_path)
            if not diff_file:
                return []
            diff_linenos = diff_file.diff_linenos
        _logger.info(f'Checking {abs_path}')

        elements: dict[etree._Element, Element] = {}
        def convert_element(element: etree._Element) -> Element:
            if element in elements:
                return elements[element]
            e = elements[element] = Element(element)
            return e

        with open(abs_path, 'rb') as fp:
            previous_line = 1
            event_elements = [
                (event, convert_element(element))
                for event, element in etree.iterparse(fp, events=('start', 'end', 'comment', 'pi'))
            ]
            for event, element in event_elements:
                if event == 'start':
                    # element.sourceline is the line number of the last line of the start tag
                    if any(line in diff_linenos for line in range(previous_line, element.sourceline + 1)):
                        element.start_tag_linenos = (previous_line, element.sourceline)
                        element.start_tag_in_diff = True
                    previous_line = element.sourceline
                    if element.text:
                        previous_line += element.text.count('\n')
                elif event == 'end':
                    # We assume the end tag is always on a single line.
                    # Bad example that we don't support:
                    #     </record
                    #     >
                    if element.tail:
                        previous_line += element.tail.count('\n')
                    element.end_tag_lineno = previous_line
                else:  # 'comment', 'pi'
                    previous_line = element.sourceline
                    if element.tail:
                        previous_line += element.tail.count('\n')
        return [element for event, element in event_elements if event == 'start']

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
            _logger.info(f'Processing diff file: {file_path}')
            
            try:
                with open(file_path, 'r') as f:
                    repo_path = f.readline().strip()
                    if not os.path.isdir(repo_path):
                        _logger.warning(f'Invalid repository path: {repo_path}')
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
                _logger.error(f'Error processing diff file {file_path}: {e}')
