from odoo.addons.aumet.cli.products_server import serve
from odoo.cli import Command


class rpc_listener(Command):
    def run(self,args):
        print("@@@@@@@@@@@@@")
        serve()
