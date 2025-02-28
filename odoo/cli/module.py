import logging
from collections import defaultdict

from odoo.addons.base.models.ir_module import STATES
from odoo.cli import Command, Subcommand, SubcommandsMixin
from odoo.orm.domains import Domain


SEP = '\n'
STATE_CHOICES = [x.replace(" ", "_") for x, y in STATES]


class ModuleList(Subcommand):
    """ Prints a list of modules """
    description = "Prints a list of modules"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parser.add_argument('--database', '-d', dest='db_name', required=True,
            help="Specify the database name.")
        self.parser.add_argument('--sort', action="store_true",
             help="Sort by name")
        self.parser.add_argument('--separator', dest='sep',
            choices=[',', '\\n', '\\t'], default='\\n',
            help="Separator")

        self.parser.add_argument('--states', nargs="*", choices=STATE_CHOICES,
            help="Include all modules with the given states")
        self.parser.add_argument('--include', nargs='*',
            help="Module name patterns (=ilike) to be included")
        self.parser.add_argument('--exclude', nargs='*',
            help="Module name patterns (=ilike) to be excluded")

        self.parser.add_argument('--parents',
            help="Select modules that this module depends on")
        self.parser.add_argument('--children',
            help="Select modules that depend on this module")
        self.parser.add_argument('--log', action="store_true",
            help="Output also contains Odoo's starting log entries")

    def _parse_args(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        parsed_args.states = [s.replace("_", " ") for s in (parsed_args.states or [])]
        match parsed_args.sep:
            case '\\n':
                parsed_args.sep = '\n'
            case '\\t':
                parsed_args.sep = '\t'
        return parsed_args

    def get_all_dependencies(self):
        deps = defaultdict(lambda: self.env['ir.module.module'])
        reverse = deps.copy()
        for dep in self.env['ir.module.module.dependency'].search([]):
            deps[dep.module_id] |= dep.depend_id
            reverse[dep.depend_id] |= dep.module_id
        return deps, reverse

    def get_parents(self, deps, module):
        buffer = [module]
        visited = module
        while buffer:
            current = buffer.pop()
            visited |= current
            buffer += deps[current]
        return visited

    def get_children(self, reverse, module):
        buffer = [module]
        visited = module
        while buffer:
            current = buffer.pop()
            buffer += reverse[current]
            visited |= current
        return visited

    def _get_domain(self, parsed_args):
        domains = []
        if parsed_args.states:
            domains.append(('state', "in", parsed_args.states))
        if parsed_args.include:
            domains.append(Domain.OR([
                [('name', '=ilike', module_pattern)]
                for module_pattern in (parsed_args.include or [])
            ]))
        if parsed_args.exclude:
            domains.append(Domain.AND([
                [('name', 'not =ilike', module_pattern)]
                for module_pattern in (parsed_args.exclude or [])
            ]))
        return Domain.AND(domains)

    def _module_search(self, module_name):
        return self.env['ir.module.module'].search([('name', '=', module_name)])

    def run(self, cmdargs):
        try:
            # Ensure arguments are consistent
            parsed_args = self._parse_args(cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        # Start a new environment, create/init the database if needed
        min_log_level = None if parsed_args.log else logging.WARNING
        with self.build_env(parsed_args.db_name, min_log_level=min_log_level) as env:
            self.env = env
            modules = self.env['ir.module.module'].search(self._get_domain(parsed_args))
            if parsed_args.parents or parsed_args.children:
                deps, reverse = self.get_all_dependencies()
                if parsed_args.parents:
                    modules &= self.get_parents(deps, self._module_search(parsed_args.parents))
                if parsed_args.children:
                    modules &= self.get_children(reverse, self._module_search(parsed_args.children))
            module_names = [m.name for m in modules]
            if parsed_args.sort:
                module_names = sorted(module_names)
            if parsed_args.exclude:
                module_names = [x for x in module_names if x not in parsed_args.exclude]
            print(parsed_args.sep.join(module_names))


class Module(Command, SubcommandsMixin):
    """ Manage Odoo modules """
    subcommands = [ModuleList]
