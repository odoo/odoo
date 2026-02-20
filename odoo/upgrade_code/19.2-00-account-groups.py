from __future__ import annotations

from bisect import bisect_right
import csv
from dataclasses import dataclass, field
from io import StringIO
import logging
import operator
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager

_logger = logging.getLogger(__name__)

COA_TO_MIGRATE = ['ar_base', 'ar_ex', 'ar_ri', 'bd', 'bh', 'co', 'do', 'ec', 'il', 'iq', 'jo_standard', 'kh', 'kw', 'lb', 'mx', 'mz', 'om', 'pk', 'qa', 'sk', 'ua_psbo', 'us', 'zm']


class AccountGroupGraph:
    def __init__(self):
        self.agroups = []

    def insert(self, agroup):
        index = bisect_right(self.agroups, agroup) - 1

        if index >= 0 and agroup.overlaps(self.agroups[index]):
            _logger.warning('Overlapping groups, skipping %s', agroup.xmlid)
            return

        if len(self) == 0 or len(agroup) == len(self.agroups[index]) or agroup != self.agroups[index]:
            self.agroups.insert(index + 1, agroup)
        else:
            self.agroups[index].children.insert(agroup)

    def find_parent_id(self, code):
        index = bisect_right(self.agroups, code) - 1
        if index < 0 or self.agroups[index] != code:
            return None
        if self.agroups[index].children and len(self.agroups[index].children):
            if parent_id := self.agroups[index].children.find_parent_id(code):
                return parent_id

        return self.agroups[index].xmlid

    def __len__(self):
        return len(self.agroups)


@dataclass(frozen=True)
class AccountGroup:  # noqa: PLW1641
    start: str
    end: str
    xmlid: str
    children: AccountGroupGraph = field(default_factory=AccountGroupGraph)

    def __post_init__(self):
        if len(self.start) != len(self.end):
            raise ValueError(f'start and end must have the same length: {self.start} - {self.end}')

        if self.start > self.end:
            raise ValueError(f'start must be <= end: {self.start} - {self.end}')

    def overlaps(self, other_group):
        if len(self) != len(other_group):
            return False
        return not (self.end < other_group.start or self.start > other_group.end)

    def __len__(self):
        return len(self.start)

    def __lt__(self, other_group):
        if isinstance(other_group, AccountGroup):
            min_len = min(len(self), len(other_group))
            if len(self) != len(other_group) and self.start[:min_len] == other_group.start[:min_len]:
                return len(self) < len(other_group)
            return self.end[:min_len] < other_group.start[:min_len]
        elif isinstance(other_group, str):
            return self.end < other_group[:len(self)]
        return NotImplemented

    def __gt__(self, other_group):
        if isinstance(other_group, str):
            return self.start > other_group[:len(self)]
        return not (self < other_group or self == other_group)

    def __eq__(self, other_group):
        if isinstance(other_group, AccountGroup):
            min_len = min(len(self), len(other_group))
            return self.start[:min_len] == other_group.start[:min_len] and self.end[:min_len] == other_group.end[:min_len]
        elif isinstance(other_group, str):
            return self.start <= other_group[:len(self)] <= self.end
        return NotImplemented


def csv_template_file_to_coa(file, model):
    return (
        file.path.suffix == '.csv'
        and file.path.parts[-2] == 'template'
        and file.path.stem.startswith(f'{model}-')
        and (coa := file.path.stem.removeprefix(f'{model}-').removesuffix('.csv')) in COA_TO_MIGRATE
        and (country_code := coa.split('_')[0])
        and (f'l10n_{country_code}' in file.path.parts or f'l10n_{country_code}_account' in file.path.parts)
    ) and coa


def coa_to_groups_coa(coa):
    if coa.startswith('ar_'):
        return 'ar_base'
    return coa


def upgrade(file_manager: FileManager):
    group_files = {
        coa: f for f in file_manager if (coa := csv_template_file_to_coa(f, 'account.group'))
    }
    account_files = {
        coa: f for f in file_manager if (coa := csv_template_file_to_coa(f, 'account.account'))
    }

    created_groups_xmlids = set()

    for i, coa in enumerate(COA_TO_MIGRATE, 1):
        gfile = group_files[coa_to_groups_coa(coa)]
        afile = account_files[coa]
        gcsv = csv.DictReader(gfile.content.splitlines())
        acsv = csv.DictReader(afile.content.splitlines())

        new_afields = acsv.fieldnames.copy()
        new_afields.insert(new_afields.index('id') + 1, 'parent_id')
        if 'active' not in new_afields:
            new_afields.insert(new_afields.index('parent_id') + 1, 'active')

        buffer = StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=new_afields,
            delimiter=',',
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            lineterminator='\n',
        )
        writer.writeheader()

        accounts = []
        codes = set()
        for row in acsv:
            index = bisect_right(accounts, row['code'], key=operator.itemgetter('code'))
            accounts.insert(index, row)
            codes.add(row['code'])

        agroups = AccountGroupGraph()
        for row in gcsv:
            parent_id = agroups.find_parent_id(row['code_prefix_start'])
            code_prefix_end = row.get('code_prefix_end') or row['code_prefix_start']
            try:
                agroup = AccountGroup(row['code_prefix_start'], code_prefix_end, row['id'])
            except ValueError as e:
                _logger.warning('Skipping group: %s', e)
                continue
            child_account_index = bisect_right(accounts, agroup, key=operator.itemgetter('code')) - 1
            if child_account_index < 0 or child_account_index >= len(accounts) or accounts[child_account_index]['code'] != agroup:
                _logger.warning('Skipping group because no account type found for it: %s', agroup.xmlid)
                continue

            account_type = accounts[child_account_index]['account_type']
            agroups.insert(agroup)

            if coa.startswith('ar_'):
                if agroup.xmlid in created_groups_xmlids:
                    continue
                else:
                    created_groups_xmlids.add(agroup.xmlid)

            code = row['code_prefix_start'] if row['code_prefix_start'] == code_prefix_end else f'{row['code_prefix_start']}-{code_prefix_end}'
            if row['code_prefix_start'] == code_prefix_end and code_prefix_end in codes:
                code = ''
            writer.writerow({
                **{k: v for k, v in row.items() if k in ('id', 'name') or k.startswith('name@')},
                'parent_id': parent_id,
                'code': code,
                'account_type': account_type,
                'active': False,
            })

        for account in accounts:
            parent_id = agroups.find_parent_id(account['code'])
            writer.writerow({
                **account,
                'active': account.get('active', True),
                'parent_id': parent_id,
            })
        afile.content = buffer.getvalue()

        file_manager.print_progress(i, len(COA_TO_MIGRATE), gfile.path)
