import code


class Console(code.InteractiveConsole):

    def __init__(self, locals=None, filename="<console>", histfile=None):
        code.InteractiveConsole.__init__(self, locals, filename)
        try:
            import readline
        except ImportError:
            pass
        else:
            try:
                import rlcompleter
                readline.set_completer(rlcompleter.Completer(locals).complete)
            except ImportError:
                pass
            readline.parse_and_bind("tab: complete")
        self.interact()
