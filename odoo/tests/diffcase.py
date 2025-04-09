import logging
import os
import re
import subprocess

from collections import defaultdict
from lxml import etree
from typing import Generator, Literal

from unidiff import PatchSet, PatchedFile

import odoo.addons

from .common import BaseCase
from odoo.tests import tagged
from odoo.tools import OrderedSet, config, lazy_property
from odoo.tools.which import which

_logger = logging.getLogger(__name__)


class FileInfo:
    root_path = os.path.abspath(config.root_path)
    addons_paths = [
        os.path.normpath(os.path.normcase(addons_path)) + os.sep
        for addons_path in odoo.addons.__path__
    ]

    def __init__(self, repo_path: str, patched_file: PatchedFile):
        abs_path = os.path.join(repo_path, patched_file.path)

        self.abs_path = abs_path  # /Users/username/project/odoo/odoo/addons/base/models/res_partner.py
        """ absolute path of the file """

        self.odoo_path: str = self.parse_odoo_path(self.abs_path)  # base/models/res_partner.py
        """ relative path of the file to one of the odoo addons path """

        self.module_name: str = self.odoo_path.split(os.sep)[0]  # base
        """ module name of the file """

        self.module_path: str = self.odoo_path[len(self.module_name) + len(os.sep):]  # models/res_partner.py
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
    def parse_odoo_path(cls, abs_path: str) -> str:
        """ parse the odoo path from the given absolute path """
        for addons_path in cls.addons_paths:
            if abs_path.startswith(addons_path) and len(abs_path) > len(addons_path):
                odoo_path = abs_path[len(addons_path):].strip(os.sep)
                return odoo_path
        return ''
    
    def is_lineno_in_diff(self, start_lineno: int, end_lineno: int = 0) -> bool:
        """ check if the given lines [start_lineno, end_lineno] inclusively are in the diff """
        if not end_lineno:
            end_lineno = start_lineno
        return any(line_no in self.diff_linenos for line_no in range(start_lineno, end_lineno + 1))


class Element:
    __slots__ = ('start_lineno', 'end_lineno', '_element')

    def __init__(self, element: etree._Element):
        self._element = element
    
    def __getattr__(self, name: str):
        if name in self.__slots__:
            return getattr(self, name)
        return getattr(self._element, name)


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
        _logger.warning(f"Cannot get git base version for {repo_path}: {e}")
        return ''

    # master-xxx / saas-18.1-xxx / 18.0-xxx
    pattern = r'^(master|saas-\d+\.\d+|\d+\.\d+)(?:-|$)'
    match = re.match(pattern, branch_name)
    if match:
        return match.group(1)
    _logger.warning(f"Cannot get git base version of {branch_name} for {repo_path}")
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
        diff_file_path = os.path.join(output_dir, f"{repo_names[repo]}_diff.txt")

        try:
            git = which('git')
            diff_command = [git, "diff", "--unified=0", "--merge-base", base_version]

            with open(diff_file_path, 'w') as f:
                f.write(f"{repo}\n")  # Write repo path as first line

                diff_output = subprocess.run(
                    diff_command,
                    capture_output=True,
                    check=False,
                    text=True,
                    cwd=repo
                ).stdout
                
                f.write(diff_output)

            _logger.info(f"Generated diff file for {repo} at {diff_file_path}")

        except Exception as e:
            _logger.warning(f"Cannot generate diff for {repo}:\n{e}")


class DiffCase(BaseCase):
    test_tags = {'no_install', 'standard'}

    diff_linenos: dict[Literal['python', 'xml'], dict[str, FileInfo]] | None = None
    """ {file_category: {abs_path: file_info}} """    

    diff_dir: str | None = None
    """ Path to a directory containing .txt diff files """

    report: list[dict] = []

    @classmethod
    def get_xml_diff_elements(cls, abs_path: str, diff_linenos: set[int] | None = None) -> Generator[Element, None, None]:
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
                        e = Element(element)
                        e.start_lineno = previous_line
                        e.end_lineno = element.sourceline
                        yield e
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

    @classmethod
    def setUpClass(cls):
        """Parse a custom diff file and initialize the diff_linenos dictionary
        
        :param diff_path: Path to a directory containing .txt diff files
        
        The expected format of each .txt file:
        - First line: Repository path
        - Remaining lines: Output of 'git diff --unified=0 base_version'
        """
        if cls.diff_linenos is not None:
            return
        cls.diff_linenos = defaultdict(dict)

        if cls.diff_dir is None:
            raise ValueError("DiffCase.diff_dir is not set")
        if not os.path.isdir(cls.diff_dir):
            raise ValueError(f"'{cls.diff_dir}' is not a directory")

        for filename in os.listdir(cls.diff_dir):
            if not filename.endswith('.txt'):
                continue

            file_path = os.path.join(cls.diff_dir, filename)
            _logger.info(f"Processing diff file: {file_path}")
            
            try:
                with open(file_path, 'r') as f:
                    repo_path = f.readline().strip()

                    if not repo_path:
                        _logger.warning(f"Empty diff file: {file_path}")
                        continue

                    if not os.path.isdir(repo_path):
                        _logger.warning(f"Invalid repository path: {repo_path}")
                        continue

                    # Read the rest of the file content for diff
                    diff_content = f.read()

                    # Parse diff using unidiff
                    if PatchSet is None:
                        raise ImportError("unidiff is not installed")
                    patch_set = PatchSet.from_string(diff_content)

                    # Process each patched file
                    for patched_file in patch_set:
                        abs_path = os.path.join(repo_path, patched_file.path)
                        file_info = FileInfo(repo_path, patched_file)

                        # Add line numbers from the diff
                        for hunk in patched_file:
                            for line in hunk:
                                if line.is_added and line.target_line_no:
                                    file_info.diff_linenos.add(line.target_line_no)

                        # Store the file info based on file type
                        if abs_path.endswith('.py'):
                            cls.diff_linenos['python'][abs_path] = file_info
                        elif abs_path.endswith('.xml'):
                            cls.diff_linenos['xml'][abs_path] = file_info

            except Exception as e:
                _logger.error(f"Error processing diff file {file_path}: {e}")
