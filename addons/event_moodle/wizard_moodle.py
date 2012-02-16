from osv import fields,osv


class moodle_config_memory(osv.osv_memory):
    _name = 'moodle.config.memory'
    _columns = {
        'hostname': fields.char('Name',64),
        'token': fields.char('test',64),
        'user_moodle': fields.char('teste',64),
        'pass_moodle': fields.char('ssss',64),
    }


    def get_connect_moodle_info(self, cr, uid, context=None):
         if not context:
             return False
         else:	
             return context.get('hostname')
