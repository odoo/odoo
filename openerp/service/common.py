# -*- coding: utf-8 -*-

import logging
import threading

import openerp.osv.orm # TODO use openerp.exceptions
import openerp.pooler
import openerp.release
import openerp.tools

import security

_logger = logging.getLogger(__name__)

RPC_VERSION_1 = {
        'server_version': openerp.release.version,
        'server_version_info': openerp.release.version_info,
        'server_serie': openerp.release.serie,
        'protocol_version': 1,
}

def dispatch(method, params):
    if method in ['login', 'about', 'timezone_get', 'get_server_environment',
                  'login_message','get_stats', 'check_connectivity',
                  'list_http_services', 'version', 'authenticate']:
        pass
    elif method in ['get_available_updates', 'get_migration_scripts', 'set_loglevel', 'get_os_time', 'get_sqlcount']:
        passwd = params[0]
        params = params[1:]
        security.check_super(passwd)
    else:
        raise Exception("Method not found: %s" % method)

    fn = globals()['exp_' + method]
    return fn(*params)

def exp_login(db, login, password):
    # TODO: legacy indirection through 'security', should use directly
    # the res.users model
    res = security.login(db, login, password)
    msg = res and 'successful login' or 'bad login or password'
    _logger.info("%s from '%s' using database '%s'", msg, login, db.lower())
    return res or False

def exp_authenticate(db, login, password, user_agent_env):
    res_users = openerp.pooler.get_pool(db).get('res.users')
    return res_users.authenticate(db, login, password, user_agent_env)

def exp_version():
    return RPC_VERSION_1

def exp_about(extended=False):
    """Return information about the OpenERP Server.

    @param extended: if True then return version info
    @return string if extended is False else tuple
    """

    info = _('See http://openerp.com')

    if extended:
        return info, openerp.release.version
    return info

def exp_timezone_get(db, login, password):
    return openerp.tools.misc.get_server_timezone()

def exp_get_available_updates(contract_id, contract_password):
    import openerp.tools.maintenance as tm
    try:
        rc = tm.remote_contract(contract_id, contract_password)
        if not rc.id:
            raise tm.RemoteContractException('This contract does not exist or is not active')

        return rc.get_available_updates(rc.id, openerp.modules.get_modules_with_version())

    except tm.RemoteContractException, e:
        raise openerp.osv.orm.except_orm('Migration Error', str(e))


def exp_get_migration_scripts(contract_id, contract_password):
    import openerp.tools.maintenance as tm
    try:
        rc = tm.remote_contract(contract_id, contract_password)
        if not rc.id:
            raise tm.RemoteContractException('This contract does not exist or is not active')
        if rc.status != 'full':
            raise tm.RemoteContractException('Can not get updates for a partial contract')

        _logger.info('starting migration with contract %s', rc.name)

        zips = rc.retrieve_updates(rc.id, openerp.modules.get_modules_with_version())

        from shutil import rmtree, copytree, copy

        backup_directory = os.path.join(openerp.tools.config['root_path'], 'backup', time.strftime('%Y-%m-%d-%H-%M'))
        if zips and not os.path.isdir(backup_directory):
            _logger.info('create a new backup directory to store the old modules: %s', backup_directory)
            os.makedirs(backup_directory)

        for module in zips:
            _logger.info('upgrade module %s', module)
            mp = openerp.modules.get_module_path(module)
            if mp:
                if os.path.isdir(mp):
                    copytree(mp, os.path.join(backup_directory, module))
                    if os.path.islink(mp):
                        os.unlink(mp)
                    else:
                        rmtree(mp)
                else:
                    copy(mp + 'zip', backup_directory)
                    os.unlink(mp + '.zip')

            try:
                try:
                    base64_decoded = base64.decodestring(zips[module])
                except Exception:
                    _logger.error('unable to read the module %s', module)
                    raise

                zip_contents = StringIO(base64_decoded)
                zip_contents.seek(0)
                try:
                    try:
                        openerp.tools.extract_zip_file(zip_contents, openerp.tools.config['addons_path'] )
                    except Exception:
                        _logger.error('unable to extract the module %s', module)
                        rmtree(module)
                        raise
                finally:
                    zip_contents.close()
            except Exception:
                _logger.error('restore the previous version of the module %s', module)
                nmp = os.path.join(backup_directory, module)
                if os.path.isdir(nmp):
                    copytree(nmp, openerp.tools.config['addons_path'])
                else:
                    copy(nmp+'.zip', openerp.tools.config['addons_path'])
                raise

        return True
    except tm.RemoteContractException, e:
        raise openerp.osv.orm.except_orm('Migration Error', str(e))
    except Exception, e:
        _logger.exception('Exception in get_migration_script:')
        raise

def exp_get_server_environment():
    os_lang = '.'.join( [x for x in locale.getdefaultlocale() if x] )
    if not os_lang:
        os_lang = 'NOT SET'
    environment = '\nEnvironment Information : \n' \
                 'System : %s\n' \
                 'OS Name : %s\n' \
                 %(platform.platform(), platform.os.name)
    if os.name == 'posix':
        if platform.system() == 'Linux':
            lsbinfo = os.popen('lsb_release -a').read()
            environment += '%s'% lsbinfo
        else:
            environment += 'Your System is not lsb compliant\n'
    environment += 'Operating System Release : %s\n' \
                'Operating System Version : %s\n' \
                'Operating System Architecture : %s\n' \
                'Operating System Locale : %s\n'\
                'Python Version : %s\n'\
                'OpenERP-Server Version : %s'\
                %(platform.release(), platform.version(), platform.architecture()[0],
                  os_lang, platform.python_version(), openerp.release.version)
    return environment

def exp_login_message():
    return openerp.tools.config.get('login_message', False)

def exp_set_loglevel(loglevel, logger=None):
    # TODO Previously, the level was set on the now deprecated
    # `openerp.netsvc.Logger` class.
    return True

def exp_get_stats():
    res = "OpenERP server: %d threads\n" % threading.active_count()
    res += netsvc.Server.allStats()
    return res

def exp_list_http_services():
    return http_server.list_http_services()

def exp_check_connectivity():
    return bool(sql_db.db_connect('postgres'))

def exp_get_os_time():
    return os.times()

def exp_get_sqlcount():
    if not logging.getLogger('openerp.sql_db').isEnabledFor(logging.DEBUG):
        _logger.warning("Counters of SQL will not be reliable unless logger openerp.sql_db is set to level DEBUG or higer.")
    return sql_db.sql_counter

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
