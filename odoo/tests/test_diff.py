import json
import subprocess
import argparse
import os

HERE = os.path.dirname(os.path.realpath(__file__))

if __name__ == '__main__':

    pypath = HERE + os.pathsep + os.environ.get('PYTHONPATH', '')
    env = dict(os.environ, PYTHONPATH=pypath)

    parser = argparse.ArgumentParser()
    parser.add_argument('--files')
    args = parser.parse_args()
    try:
        process = subprocess.Popen(['pylint', '--output-format', 'json', '--disable=all', '--enable=non-const-markup', '--load-plugins=_odoo_checker_markup'] + args.files.split(","), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, IOError):
        print('pylint executable not found in the path')
    else:
        out, err = process.communicate()
        result_dict = {}
        result = json.loads(out.decode())
        for line in result:
            lineno = 'line %s-%d' % (line['line'], int(line['column'])+int(line['line'])-1)
            if not result_dict.get(line['path']):
                result_dict[line['path']] = {}
            result_dict[line['path']].update({lineno: '%s : %s' % (line['message-id'], line['message'])})
        print(result_dict.__repr__().replace("'", '"'))
