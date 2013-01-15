import argparse
import textwrap

from .call import Call
from .client import Open, Show, ConsumeNothing, ConsumeMemory, LeakMemory, ConsumeCPU
from .benchmarks import Bench, BenchRead, BenchFieldsViewGet, BenchDummy, BenchLogin
from .bench_sale_mrp import BenchSaleMrp
from . import common

from . import conf # Not really server-side (in the `for` below).
from . import drop
from . import initialize
from . import model
from . import module
from . import read
from . import run_tests
from . import scaffold
from . import uninstall
from . import update

command_list_server = (conf, drop, initialize, model, module, read, run_tests,
                       scaffold, uninstall, update, )

command_list_client = (Call, Open, Show, ConsumeNothing, ConsumeMemory,
                       LeakMemory, ConsumeCPU, Bench, BenchRead,
                       BenchFieldsViewGet, BenchDummy, BenchLogin,
                       BenchSaleMrp, )

def main_parser():
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=textwrap.fill(textwrap.dedent("""\
                    OpenERP Command provides a set of command-line tools around
                    the OpenERP framework: openobject-server. All the tools are
                    sub-commands of a single oe executable.""")),
        epilog="""Use <command> --help to get information about the command.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    description = []
    for x in command_list_server:
        description.append(x.__name__[len(__package__)+1:])
        if x.__doc__:
            description.extend([
                ":\n",
                textwrap.fill(str(x.__doc__).strip(),
                              subsequent_indent='  ',
                              initial_indent='  '),
            ])
        description.append("\n\n")
    subparsers = parser.add_subparsers(
        title="Available commands",
        help=argparse.SUPPRESS,
        description="".join(description[:-1]),
    )
    # Server-side commands.
    for x in command_list_server:
        x.add_parser(subparsers)
    # Client-side commands. TODO one per .py file.
    for x in command_list_client:
        x(subparsers)
    return parser
