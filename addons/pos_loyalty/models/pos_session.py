# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['loyalty.program', 'loyalty.rule', 'loyalty.reward', 'loyalty.card']
        return data

<<<<<<< HEAD
||||||| parent of 5cf87f578b6e (temp)
        return params

    def _replace_ilike_with_in(self, domain_str):
        if domain_str == "null":
            return domain_str

        domain = ast.literal_eval(domain_str)

        for index, condition in enumerate(domain):
            if isinstance(condition, (list, tuple)) and len(condition) == 3:
                field_name, operator, value = condition
                field = self.env['product.product']._fields.get(field_name)

                if field and field.type == 'many2one' and operator in ('ilike', 'not ilike'):
                    comodel = self.env[field.comodel_name]
                    matching_ids = list(comodel._name_search(value, [], operator, limit=None))

                    new_operator = 'in' if operator == 'ilike' else 'not in'
                    domain[index] = [field_name, new_operator, matching_ids]

        return json.dumps(domain)

    def load_data(self, models_to_load, only_data=False):
        result = super().load_data(models_to_load, only_data)

        # adapt product
        if len(models_to_load) == 0 or 'product.product' in models_to_load:
            product_params = self._load_data_params(self.config_id)['product.product']
            rewards = self.config_id._get_program_ids().reward_ids
            reward_products = rewards.discount_line_product_id | rewards.reward_product_ids
            trigger_products = self.config_id._get_program_ids().filtered(lambda p: p.program_type == 'ewallet').trigger_product_ids

            products = list(set(reward_products.ids + trigger_products.ids) - set(product['id'] for product in result['data']['product.product']))
            products = self.env['product.product'].search_read([('id', 'in', products)], fields=product_params['fields'], load=False)
            self._process_pos_ui_product_product(products)

            result['custom']['pos_special_products_ids'].extend(
                [product.id for product in reward_products if product.id not in [p["id"] for p in result['data']['product.product']]]
            )
            result['data']['product.product'].extend(products)

        # adapt loyalty
        if len(models_to_load) == 0 or 'loyalty.reward' in models_to_load:
            for reward in result['data']['loyalty.reward']:
                reward['reward_product_domain'] = self._replace_ilike_with_in(reward['reward_product_domain'])

        return result
=======
        return params

    def _replace_ilike_with_in(self, domain_str):
        if domain_str == "null":
            return domain_str

        domain = ast.literal_eval(domain_str)

        for index, condition in enumerate(domain):
            if isinstance(condition, (list, tuple)) and len(condition) == 3:
                field_name, operator, value = condition
                field = self.env['product.product']._fields.get(field_name)

                if field and field.type == 'many2one' and operator in ('ilike', 'not ilike'):
                    comodel = self.env[field.comodel_name]
                    matching_ids = list(comodel._name_search(value, [], operator, limit=None))

                    new_operator = 'in' if operator == 'ilike' else 'not in'
                    domain[index] = [field_name, new_operator, matching_ids]

        return json.dumps(domain)

    def load_data(self, models_to_load, only_data=False):
        result = super().load_data(models_to_load, only_data)

        # adapt product
        if len(models_to_load) == 0 or 'product.product' in models_to_load:
            product_params = self._load_data_params(self.config_id)['product.product']
            rewards = self.config_id._get_program_ids().reward_ids
            reward_products = rewards.discount_line_product_id | rewards.reward_product_ids
            trigger_products = self.config_id._get_program_ids().filtered(lambda p: p.program_type in ['ewallet', 'gift_card']).trigger_product_ids

            products = list(set(reward_products.ids + trigger_products.ids) - set(product['id'] for product in result['data']['product.product']))
            products = self.env['product.product'].search_read([('id', 'in', products)], fields=product_params['fields'], load=False)
            self._process_pos_ui_product_product(products)

            result['custom']['pos_special_products_ids'].extend(
                [product.id for product in reward_products if product.id not in [p["id"] for p in result['data']['product.product']]]
            )
            result['data']['product.product'].extend(products)

        # adapt loyalty
        if len(models_to_load) == 0 or 'loyalty.reward' in models_to_load:
            for reward in result['data']['loyalty.reward']:
                reward['reward_product_domain'] = self._replace_ilike_with_in(reward['reward_product_domain'])

        return result
>>>>>>> 5cf87f578b6e (temp)
