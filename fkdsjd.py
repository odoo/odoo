PATH = "/home/julien/Projects/odoo-community/odoo/config.py"

with open(PATH) as fd:
    lines = fd.readlines()

import re

s = lambda x: x and "'%s'" % x.strip('\'"').replace("'", "\'")
d = lambda x: x and '"%s"' % x.strip('\'"').replace('"', '\"')
patterns = [
    r"""\s*add\(""",
    r"""["'](?P<uniflag>-[a-zA-Z])["'], """,
    r"""["'](?P<multiflag>--[\w\-]+)["'], """,
    r"""dest=["'](?P<dest>\w+)["'], """,
    r"""action=["'](?P<action>\w+)["'], """,
    r"""type=(?P<type>[^,]+), """,
    r"""default=(?P<default>[^ ]+), """,
    r"""metavar=(?P<metavar>["'][\w\- ]+["']), """,
    r"""choices=(?P<choices>[^,]+), """,
    r"""const=(?P<const>[^,]+), """,
    r"""envvar=["'](?P<envvar>\w+)["'], """,
    r"""help=(?P<help>.*)""",
    r""".*\)?"""
]
#print(patterns)
#print("".join(str(i % 10) for i in range(len(patterns))))
#print("".join(str((i // 10) % 10) if i % 10 == 0 else " " for i in range(len(patterns))))

res = [re.compile(p) for p in patterns]

for line in lines:
    if not line.strip().startswith("add("):
        continue

    g = {}
    for r in res:
        m = r.search(line)
        if m:
            g.update(m.groupdict())

    lines = {
        'beg': f"OptionSpec(server, '', ",
        'dest': f"{s(g['dest'])}, ",
        'short': f"short_flag={d(g.get('uniflag'))}, ",
        'long': f"long_flag={d(g['multiflag'])}, ",
        'type': f"type={g.get('type', 'str')}, ",
        'rtype': "rtype=str, " if 'comma' not in g.get('type', '') else "rtype=','.join, ",
        'action': f"action={s(g.get('action', 'store'))}, ",
        'default': f"default={g.get('default', 'None')}, ",
        'const': f"const={g.get('const', 'None')}, ",
        'envvar': f"envvar={s(g.get('envvar')) or 'None'}, ",
        'metavar': f"metavar={s(g.get('metavar')) or 'None'}, ",
        'help': f"help={g.get('help', '')}",
    }
    if 'const' not in g:
        del lines['const']
    if 'uniflag' not in g:
        del lines['short']
    print("".join(lines.values()))


