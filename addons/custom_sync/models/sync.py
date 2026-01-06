import xmlrpc.client
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class JokerSyncConfig(models.Model):
    _name = 'joker.sync.config'
    _description = 'Joker Sync Configuration'

    name = fields.Char(string='Bağlantı Adı', required=True, default='Enterprise Connection')
    url = fields.Char(string='URL', required=True)
    database = fields.Char(string='Veritabanı', required=True)
    username = fields.Char(string='Kullanıcı Adı', required=True)
    password = fields.Char(string='Şifre', required=True)
    api_key = fields.Char(string='API Key')
    active = fields.Boolean(string='Aktif', default=True)
    last_sync = fields.Datetime(string='Son Senkronizasyon')
    sync_interval = fields.Integer(string='Senkronizasyon Aralığı (dk)', default=5)
    
    state = fields.Selection([
        ('disconnected', 'Bağlantı Yok'),
        ('connected', 'Bağlı'),
        ('error', 'Hata')
    ], string='Durum', default='disconnected')

    def test_connection(self):
        """Bağlantıyı test et"""
        self.ensure_one()
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            uid = common.authenticate(self.database, self.username, self.password, {})
            if uid:
                self.state = 'connected'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Başarılı',
                        'message': f'Bağlantı başarılı! UID: {uid}',
                        'type': 'success',
                    }
                }
            else:
                self.state = 'error'
                raise UserError('Kimlik doğrulama başarısız!')
        except Exception as e:
            self.state = 'error'
            raise UserError(f'Bağlantı hatası: {str(e)}')


class JokerSyncLog(models.Model):
    _name = 'joker.sync.log'
    _description = 'Joker Sync Log'
    _order = 'create_date desc'

    name = fields.Char(string='İşlem', required=True)
    model_name = fields.Char(string='Model')
    record_count = fields.Integer(string='Kayıt Sayısı', default=0)
    direction = fields.Selection([
        ('pull', 'Çekme (Pull)'),
        ('push', 'Gönderme (Push)')
    ], string='Yön')
    state = fields.Selection([
        ('success', 'Başarılı'),
        ('error', 'Hata'),
        ('partial', 'Kısmi')
    ], string='Durum')
    error_message = fields.Text(string='Hata Mesajı')
    duration = fields.Float(string='Süre (sn)')


class JokerSync(models.Model):
    _name = 'joker.sync'
    _description = 'Joker Sync Engine'

    @api.model
    def _get_connection(self):
        """Enterprise sunucusuna bağlantı kur"""
        config = self.env['joker.sync.config'].search([('active', '=', True)], limit=1)
        if not config:
            _logger.warning('Aktif senkronizasyon yapılandırması bulunamadı!')
            return None, None, None
        
        try:
            common = xmlrpc.client.ServerProxy(f'{config.url}/xmlrpc/2/common')
            uid = common.authenticate(config.database, config.username, config.password, {})
            
            if uid:
                models = xmlrpc.client.ServerProxy(f'{config.url}/xmlrpc/2/object')
                return uid, models, config
            return None, None, None
        except Exception as e:
            _logger.error(f'Bağlantı hatası: {str(e)}')
            return None, None, None

    @api.model
    def sync_pull_from_enterprise(self):
        """
        Enterprise sunucusundan son 1 saatte değişen kayıtları çek
        Bu metod cron job tarafından çağrılır
        """
        start_time = datetime.now()
        uid, models_proxy, config = self._get_connection()
        
        if not uid:
            self.env['joker.sync.log'].create({
                'name': 'Pull Sync Failed',
                'direction': 'pull',
                'state': 'error',
                'error_message': 'Bağlantı kurulamadı'
            })
            return False
        
        one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        total_records = 0
        
        # Senkronize edilecek modeller
        sync_models = [
            ('res.partner', ['name', 'email', 'phone', 'street', 'city', 'country_id', 'vat', 'is_company']),
            ('product.template', ['name', 'default_code', 'list_price', 'standard_price', 'type', 'categ_id']),
            ('sale.order', ['name', 'partner_id', 'date_order', 'amount_total', 'state']),
            ('stock.quant', ['product_id', 'location_id', 'quantity', 'reserved_quantity']),
        ]
        
        for model_name, field_list in sync_models:
            try:
                # Enterprise'dan değişen kayıtları çek
                records = models_proxy.execute_kw(
                    config.database, uid, config.password,
                    model_name, 'search_read',
                    [[['write_date', '>=', one_hour_ago]]],
                    {'fields': field_list + ['write_date'], 'limit': 1000}
                )
                
                if records:
                    self._process_pulled_records(model_name, records)
                    total_records += len(records)
                    _logger.info(f'{model_name}: {len(records)} kayıt çekildi')
                    
            except Exception as e:
                _logger.error(f'{model_name} senkronizasyon hatası: {str(e)}')
        
        # Senkronizasyon logunu kaydet
        duration = (datetime.now() - start_time).total_seconds()
        config.last_sync = datetime.now()
        
        self.env['joker.sync.log'].create({
            'name': 'Pull Sync Completed',
            'direction': 'pull',
            'state': 'success',
            'record_count': total_records,
            'duration': duration
        })
        
        return True

    def _process_pulled_records(self, model_name, records):
        """Çekilen kayıtları işle ve local veritabanına kaydet"""
        LocalModel = self.env.get(model_name)
        if not LocalModel:
            return
        
        for record in records:
            # External ID ile eşleştir veya yeni kayıt oluştur
            external_id = f"joker_sync.{model_name.replace('.', '_')}_{record.get('id', 0)}"
            
            try:
                existing = self.env.ref(external_id, raise_if_not_found=False)
                
                # Sadece senkronize edilebilir alanları al
                vals = {k: v for k, v in record.items() 
                       if k not in ['id', 'write_date', 'create_date', '__last_update']}
                
                # Many2one alanları için ID'yi düzelt
                for key, value in vals.items():
                    if isinstance(value, list) and len(value) == 2:
                        vals[key] = value[0]  # ID'yi al
                
                if existing:
                    existing.write(vals)
                else:
                    new_record = LocalModel.create(vals)
                    # External ID oluştur
                    self.env['ir.model.data'].create({
                        'name': f"{model_name.replace('.', '_')}_{record.get('id', 0)}",
                        'module': 'joker_sync',
                        'model': model_name,
                        'res_id': new_record.id,
                    })
            except Exception as e:
                _logger.error(f'Kayıt işleme hatası ({model_name}): {str(e)}')

    @api.model
    def sync_push_to_enterprise(self, model_name, record_id, vals):
        """
        Local değişiklikleri Enterprise sunucusuna gönder
        Bu metod write/create override'larından çağrılır
        """
        uid, models_proxy, config = self._get_connection()
        
        if not uid:
            _logger.warning('Push sync: Bağlantı kurulamadı')
            return False
        
        try:
            # External ID'yi bul
            external_ref = self.env['ir.model.data'].search([
                ('module', '=', 'joker_sync'),
                ('model', '=', model_name),
                ('res_id', '=', record_id)
            ], limit=1)
            
            if external_ref:
                # Enterprise'da güncelle
                enterprise_id = int(external_ref.name.split('_')[-1])
                models_proxy.execute_kw(
                    config.database, uid, config.password,
                    model_name, 'write',
                    [[enterprise_id], vals]
                )
                _logger.info(f'Push sync: {model_name} ID:{enterprise_id} güncellendi')
            else:
                # Enterprise'da yeni kayıt oluştur
                new_id = models_proxy.execute_kw(
                    config.database, uid, config.password,
                    model_name, 'create',
                    [vals]
                )
                # External ID kaydet
                self.env['ir.model.data'].create({
                    'name': f"{model_name.replace('.', '_')}_{new_id}",
                    'module': 'joker_sync',
                    'model': model_name,
                    'res_id': record_id,
                })
                _logger.info(f'Push sync: {model_name} yeni kayıt ID:{new_id}')
            
            return True
            
        except Exception as e:
            _logger.error(f'Push sync hatası: {str(e)}')
            self.env['joker.sync.log'].create({
                'name': f'Push Sync Failed: {model_name}',
                'model_name': model_name,
                'direction': 'push',
                'state': 'error',
                'error_message': str(e)
            })
            return False


class ResPartnerSync(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            self.env['joker.sync'].sync_push_to_enterprise('res.partner', record.id, vals)
        return records

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            self.env['joker.sync'].sync_push_to_enterprise('res.partner', record.id, vals)
        return result


class ProductTemplateSync(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            self.env['joker.sync'].sync_push_to_enterprise('product.template', record.id, vals)
        return records

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            self.env['joker.sync'].sync_push_to_enterprise('product.template', record.id, vals)
        return result


class SaleOrderSync(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            self.env['joker.sync'].sync_push_to_enterprise('sale.order', record.id, vals)
        return records

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            self.env['joker.sync'].sync_push_to_enterprise('sale.order', record.id, vals)
        return result
