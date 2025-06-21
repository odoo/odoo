from os import environ, path
import subprocess
import sys

#This test is meant to be standalone, correct usage : python test_security.py file1 file2 file3 ...

if __name__ == '__main__':

    HERE = path.dirname(__file__)

    if 'PYTHONPATH' not in environ:
        environ['PYTHONPATH'] = HERE
    else:
        environ['PYTHONPATH'] += ':' + HERE

    command = ['pylint', '--rcfile=/dev/null', '--disable=all', '--output-format', 'json', '--enable=non-const-markup', '--reports=n', '--load-plugins=_odoo_checker_markup', *sys.argv[1:]]

    proc = subprocess.run(command, env=environ, check=True)
