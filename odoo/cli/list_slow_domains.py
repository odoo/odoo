import itertools
import json
import logging
import time
import traceback
import optparse
import heapq
from concurrent.futures import ThreadPoolExecutor
from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, api, modules
from odoo import fields
from odoo.cli.command import Command
from odoo.modules.registry import Registry
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval, datetime

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


TIME_LIMIT = 300  # 5 minutes
MAX_WORKERS = 4


class DomainObj:
    def __init__(
        self,
        domain: list,
        fields: list[str],
        model_name: str,
        domain_for: str,
        groupby: list[str] = None,  # noqa: RUF013
        having: list[str] = None,  # noqa: RUF013
        user_id: int = None,  # noqa: RUF013
    ):
        self.domain = domain
        self.fields = fields
        self.model_name = model_name
        self.domain_for = domain_for
        self.groupby = groupby or []
        self.having = having or []
        if user_id is None:
            self.user_id = SUPERUSER_ID
        else:
            self.user_id = user_id

    def __lt__(self, other):
        return len(self.domain) < len(other.domain)


class IrFilterDomain(DomainObj):
    @classmethod
    def _create_ir_filter_domain(cls, record) -> "IrFilterDomain":
        user_id = SUPERUSER_ID if not record.user_ids else record.user_ids.ids[0]
        return cls(
            domain=record._get_eval_domain(),
            fields=[],
            model_name=record.model_id,
            domain_for=record.name,
            groupby=[],
            having=[],
            user_id=user_id,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(domain={self.domain!r}, model_name={self.model_name!r}, domain_for={self.domain_for!r}, user_id={self.user_id})"


class SpreadsheetDomain(DomainObj):
    def __init__(
        self,
        domain: list,
        fields: list[str],
        model_name: str,
        domain_for: str,
        spreadsheet_id: int,
        spreadsheet_name: str,
        groupby: list[str] = None,  # noqa: RUF013
        having: list[str] = None,  # noqa: RUF013
        user_id: int = None,  # noqa: RUF013
    ):
        super().__init__(
            domain=domain,
            fields=fields,
            model_name=model_name,
            domain_for=domain_for,
            groupby=groupby,
            having=having,
            user_id=user_id,
        )
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet_name = spreadsheet_name

    def _normalize_domain(env, raw_domain):
        if isinstance(raw_domain, list):
            return raw_domain

        if isinstance(raw_domain, str):
            eval_context = {
                'uid': env.uid,
                'user': env.user,
                'datetime': datetime,
                'relativedelta': relativedelta,
                'context_today': lambda: datetime.date.today().strftime('%Y-%m-%d'),
                'current_date': fields.Date.today(),
            }
            list_domain = safe_eval(raw_domain, eval_context)

            return list_domain if isinstance(list_domain, list) else []
        return []

    @classmethod
    def _create_spreadsheet_domain(cls, env, data: dict, spreadsheet) -> "SpreadsheetDomain":
        res_model = data.get("model")
        domain = cls._normalize_domain(env, data.get("domain", []))
        having = data.get("having", [])
        data_name = data.get("name", "Unknown")

        fields = set()
        groupby = []
        model_fields = spreadsheet._fields
        for measure in data.get("measures", []):
            if "fieldName" in measure and measure["fieldName"] not in ["Ratio", "__count"]:
                field = measure["fieldName"]
                if field not in model_fields:
                    continue
                aggregator = measure.get("aggregator", "count")
                fields.add(f"{field}:{aggregator}")

        for direction in data.get("rows", []) + data.get("columns", []):
            if "fieldName" in direction:
                field = direction["fieldName"]
                if field not in model_fields:
                    continue
                granularity = ""
                if 'granularity' in direction:
                    granularity = ":" + direction['granularity']
                groupby.append(direction["fieldName"] + granularity)

        user_id = SUPERUSER_ID

        return cls(
            domain=domain,
            fields=list(fields),
            model_name=res_model,
            domain_for=data_name,
            spreadsheet_id=spreadsheet.id,
            spreadsheet_name=spreadsheet.name,
            groupby=groupby,
            having=having,
            user_id=user_id,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(model_name={self.model_name!r}, spreadsheet_id={self.spreadsheet_id!r}, spreadsheet_name={self.spreadsheet_name!r}, filter_name={self.domain_for})"


def init_registry(args):
    if args.addons_path:
        config['addons_path'] = args.addons_path
        modules.initialize_sys_path()
    db_name = args.db_name
    return Registry(db_name)


def _get_spreadsheet_domain_for_model(
    env, model_name, domain_list, batch_size=2000, limit_offset=float("inf"),
):
    if model_name not in env:
        return []

    offset = 0
    records = env[model_name].search(domain_list, limit=batch_size, offset=offset)

    def _process_batch(spreadsheet_batch):
        domains = []
        for spreadsheet in spreadsheet_batch:
            try:
                body = json.loads(spreadsheet._get_serialized_spreadsheet_data_body())
            except Exception:  # noqa: BLE001
                _logger.error("ERROR: Error Validating spreadsheet ID %d", {spreadsheet.id})
                _logger.error(traceback.format_exc())
                continue

            data = body.get("data", {})
            revisions = body.get("revisions", [])

            for pivot in data.get("pivots", {}).values():
                if pivot.get("model") is None:
                    continue
                domains.append(
                    SpreadsheetDomain._create_spreadsheet_domain(env, pivot, spreadsheet),
                )

            for list_ in data.get("lists", {}).values():
                if list_.get("model") is None:
                    continue
                domains.append(
                    SpreadsheetDomain._create_spreadsheet_domain(env, list_, spreadsheet),
                )

            for revision in revisions:
                for command in revision.get("commands", []):
                    if command["type"] in ("UPDATE_PIVOT", "ADD_PIVOT"):
                        if command['pivot'].get("model") is None:
                            continue
                        domains.append(
                            SpreadsheetDomain._create_spreadsheet_domain(
                                env, command["pivot"], spreadsheet,
                            ),
                        )
                    elif command["type"] in ("UPDATE_ODOO_LIST", "INSERT_ODOO_LIST"):
                        list_ = command.get("list", command.get("definition", {}))
                        if list_ and list_.get("model") is not None:
                            res_model = list_.get("metaData", {}).get("resModel")
                            domain = list_.get("searchParams", {}).get("domain", [])
                            domains.append(
                                SpreadsheetDomain(
                                    domain,
                                    [],
                                    res_model,
                                    spreadsheet.id,
                                    spreadsheet.name,
                                    "List View",
                                ),
                            )

        spreadsheet_batch.invalidate_recordset()
        return domains

    while records and offset < limit_offset:
        yield _process_batch(records)
        offset += 1
        records = env[model_name].search(
            domain_list, limit=batch_size, offset=offset * batch_size,
        )


def _get_ir_model_filters(env, domain, batch_size=2000, limit_offset=float("inf")):
    offset = 0
    records = env["ir.filters"].search(domain, limit=batch_size, offset=offset)

    while records and offset < limit_offset:
        ir_filters = []
        for rec in records:
            try:
                ir_filter = IrFilterDomain._create_ir_filter_domain(rec)
                ir_filters.append(ir_filter)
            except ValueError as e:
                _logger.error("ERROR: %s", e)
                _logger.error("ERROR: Error parsing %s. Skipping........", rec)
        yield ir_filters
        offset += 1
        records.invalidate_recordset()
        records = env["ir.filters"].search(
            [], limit=batch_size, offset=offset * batch_size,
        )


def _execute_domain(env, domain: DomainObj):
    with env.registry.cursor() as new_cr:
        try:
            new_env = api.Environment(new_cr, domain.user_id, env.context)
            Model = new_env.get(domain.model_name)

            if Model is None:
                raise Exception(f"Model {domain.model_name} does not exist")  # noqa: TRY301, TRY002

            if domain.groupby:
                Model._read_group(domain.domain, domain.groupby, domain.fields)
            else:
                Model.search(domain.domain)
        except Exception as e:  # noqa: BLE001
            _logger.error("ERROR: Exception processing domain %s: %s", domain, e)
            return -1

    return 0


domains_with_time = []


def _add_domain(domain, time):
    heapq.heappush(domains_with_time, (-time, domain))


def _get_top_k(k):
    top_k = []
    while k and domains_with_time:
        time, curr_domain = heapq.heappop(domains_with_time)
        # Since we pushed the negative value of the time to utiliize the structure as a max-heap.
        time *= -1

        top_k.append((curr_domain, time))
        k -= 1

    for domain, time in top_k:
        _add_domain(domain, time)

    return top_k


def _execute_child(env, domain):
    start_time = time.time()
    _execute_domain(env, domain)
    return time.time() - start_time


def _execute(env, domains):
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_domain = {
            executor.submit(_execute_child, env, domain): domain
            for domain in domains
        }
        for future, domain in future_to_domain.items():
            try:
                time_taken = future.result(timeout=TIME_LIMIT)
                _add_domain(domain, time_taken)
            except TimeoutError:
                _logger.warning("Warning: Domain (%s) with filter (%s) more than 5 minutes to execute.", domain, domain.domain_for)


def _test_domains(env, domains):
    _execute(env, domains)


def test_domains(env, domains):
    for i, domains in enumerate(domains):
        _logger.info("INFO: Testing batch %d size of %d", i + 1, len(domains))
        _test_domains(env, domains)
        top_twenty_domains = _get_top_k(20)
        _logger.info("INFO: PRINTING TOP %d SLOWEST DOMAINS", len(top_twenty_domains))
        _logger.info("=" * 70)
        for domain, time_taken in top_twenty_domains:
            _logger.info("INFO: %s executed in %f seconds", domain, time_taken)


class ExecutorCommand(Command):
    """Command-line tool to test and list the slowest domains in the database"""

    name = "list_slow_domains"
    description = "Command-line tool to test and list the slowest domains in the database"

    def run(self, cmdargs):
        parser = config.parser

        group = optparse.OptionGroup(parser, "SD Configuration")
        group.add_option(
            "-f",
            "--ir_filters",
            action="store_true",
            help="FLAG: Include and test domains extracted from 'ir.filters' records.",
        )
        group.add_option(
            "--spreadsheet_domains",
            action="store_true",
            help="FLAG: Include and test domains extracted from spreadsheet dashboards and documents.",
        )
        group.add_option(
            "--limit_offset",
            default="1",
            metavar="N",
            help="INTEGER: Limiting the number of batches to be tested for each category. "
                 "The number passed multiplies the batch size (2000). "
                 "e.g., Passing 1 will test up to 2000 records, passing 2 will test up to 4000.",
        )

        parser.add_option_group(group)

        self.batch_size = 2000
        self.init(cmdargs)

    def init(self, args):
        super().__init__()
        opt = config.parse_config(args, setup_logging=True)
        db_name = opt.db_name[0]

        db_connection_params = [
            'db_host',
            'db_port',
            'db_user',
            'db_password',
            'db_sslmode',
            'db_maxconn',
        ]

        for param in db_connection_params:
            if hasattr(opt, param) and opt.param is not None:
                config[param] = opt.param

        registry = Registry(db_name)
        self.limit_offset = 200
        _logger.info("INFO: Connecting to database: %s", {db_name})

        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            domains = self.get_domains(env, opt)
            test_domains(env, domains)

    def get_domains(self, env, args):
        search_domain = [("handler", "=", "spreadsheet")]

        if args.ir_filters:
            yield from _get_ir_model_filters(env, [], batch_size=self.batch_size, limit_offset=self.limit_offset)

        if args.spreadsheet_domains:
            yield from itertools.chain(
                _get_spreadsheet_domain_for_model(
                    env,
                    "documents.document",
                    search_domain,
                    batch_size=self.batch_size,
                    limit_offset=self.limit_offset,
                ),
                _get_spreadsheet_domain_for_model(
                    env,
                    "spreadsheet.dashboard",
                    [],
                    batch_size=self.batch_size,
                    limit_offset=self.limit_offset,
                ),
            )
