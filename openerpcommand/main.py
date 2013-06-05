import openerpcommand

def run():
    """ Main entry point for the openerp-command tool."""
    parser = openerpcommand.main_parser()
    args = parser.parse_args()
    args.run(args)
