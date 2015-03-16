from openerp import models, fields
import hashlib
import json

class request_cache_store(models.Model):
    _name = 'cache.store'

    hashkey = fields.Char(string='Cache Group Name', required=True, readonly=True)
    model   = fields.Char(string='Cached Model Name', required=True, readonly=True)
    data    = fields.Text(string='Serialized Data', required=True, readonly=True) 
    
    def init(self, cr):
        cr.execute("CREATE OR REPLACE FUNCTION invalid_cache() RETURNS TRIGGER AS ' BEGIN DELETE FROM cache_store WHERE model=TG_ARGV[0]; RETURN NEW; END; ' LANGUAGE 'plpgsql';");
        
    def archive(self, hashkey, model, input_data):
        if not hasattr(self.env[model], '_cache_dependencies'):
            return False
        input_data = json.dumps(input_data)
        try:
            return bool(self.sudo().create({'hashkey': hashkey, 'model': model, 'data': input_data}))
        except:
            return False

    def get_hash(self, *serialargs):
        hash_str = json.dumps(serialargs, sort_keys=True)
        hash_str = hashlib.md5(hash_str)
        return hash_str.hexdigest()

    def get(self, hashkey):
        result = self._cr.execute("SELECT data FROM cache_store WHERE hashkey=%s ORDER BY id LIMIT 1", (hashkey,))
        result = self._cr.fetchall()
        if not result:
            return False
        return result[0][0]

    def _register_hook(self, cr):
        super(request_cache_store, self)._register_hook(cr)
        for model in self.pool.itervalues():
            cache_dependencies = getattr(model, '_cache_dependencies', False)
            if cache_dependencies:
                models      = set()
                core_model  = model._name
                models.add(core_model)
                inherits    = model._inherits
                if inherits:
                    for m in inherits:
                        models.add(m)

                for m in cache_dependencies:
                    models.add(m)

                for model in models:
                    model = model.replace('.', '_')
                    trigger = "DROP TRIGGER IF EXISTS after_change_%s on %s; CREATE TRIGGER after_change_%s AFTER INSERT OR UPDATE OR DELETE ON %s EXECUTE PROCEDURE invalid_cache('%s');" % ((model,)*4 + (core_model,))
                    cr.execute(trigger)
