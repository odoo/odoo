#! /usr/bin/env python2
import os

import openerp
from openerp import SUPERUSER_ID

DATABASE='t'

def configure():
    conf = openerp.tools.config
    conf['addons_path'] = os.path.join(os.path.dirname(os.path.dirname(__file__))) + ",/home/thu/repos/web/trunk/addons"
    conf['log_handler'] = [':CRITICAL']
    openerp.modules.module.initialize_sys_path()
    openerp.netsvc.init_logger()

if __name__ == '__main__':
    configure()

    print '> Loading registry `%s`...' % DATABASE
    registry = registry = openerp.registry(DATABASE)
    cr = registry.db.cursor()
    print '< Registry `%s` loaded.' % DATABASE

    model = registry['test.workflow.model']
    trigger = registry['test.workflow.trigger']

    print '> Creating new record...'
    i = model.create(cr, SUPERUSER_ID, {})
    print '< Record created with ID %s' % i

    print '> Calling signal `a-b`...'
    model.signal_workflow(cr, SUPERUSER_ID, [i], 'a-b')
    print '< Signal `a-b` called.'

    print '> Triggering associated record...'
    model.trigger(cr, SUPERUSER_ID, [i])
    print '< Associated record triggered.'

    print '> Triggering associated record (this time with the condition evaluating to True)...'
    trigger.write(cr, SUPERUSER_ID, [1], {'value': True})
    model.trigger(cr, SUPERUSER_ID)
    print '< Associated record triggered.'

    cr.close()
