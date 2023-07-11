import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))

#This test is meant to be standalone, correct usage : python test_security.py file1 file2 file3 ...

if __name__ == '__main__': 

    env = os.environ
    if 'PYTHONPATH' not in env.keys():
        env.update({'PYTHONPATH': HERE})
    else:
        env.update({'PYTHONPATH': env['PYTHONPATH'] + ':' + HERE})
    
    command = ['pylint', '--rcfile=/dev/null', '--disable=all', '--output-format',  'json', '--enable=non-const-markup', '--reports=n', '--load-plugins=_odoo_checker_markup']
    command += sys.argv[1:]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, env=env)
    
    print(proc.communicate()[0].decode())