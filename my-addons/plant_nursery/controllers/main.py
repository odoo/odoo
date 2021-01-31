# -*- coding: utf-8 -*-

import random
import werkzeug

from odoo.http import Controller, request, route


class TripController(Controller):

    # Generic display pages
    # --------------------------------------------------

    @route('/hello', type='http', auth="public", website=True)
    def plants_hello(self, **post):
        return request.render("plant_nursery.plant_hello", {'name': 'World'})

    @route('/hello2', type='http', auth="public", website=True)
    def plants_hello2(self, **post):
        return request.render("plant_nursery.plant_hello2", {'name': 'World'})

    @route('/hello3', type='http', auth="public", website=True)
    def plants_hello3(self, **post):
        values = {
            'company': request.env.user.company_id.sudo(),
            'plants': request.env['nursery.plant'].search([]),
        }
        return request.render("plant_nursery.plant_hello3", values)

    @route(['/plants', '/plants/page/<int:page>'], type='http', auth="public", website=True)
    def plants(self, page=1, **post):
        plant_domain = []
        if post.get('category'):
            plant_domain += [('category_id.name', 'ilike', post['category'])]
        plants = request.env['nursery.plant'].search(plant_domain)

        values = {
            'company': request.env.user.company_id.sudo(),
            'plants': plants,
            'search': post,
            'error': post.get('error')
        }
        if post.get('order_id'):
            values['order'] = request.env['nursery.order'].browse(int(post['order_id']))

        return request.render("plant_nursery.portal_plants", values)

    @route('/plants/quote', type='http', auth="public", website=True)
    def plants_quote(self, **post):
        customer_name = post.get('customer_name')
        customer_email = post.get('customer_email')
        if not customer_name and not customer_email:
            return request.redirect('/plants')

        line_ids = []
        for key, value in post.items():
            if key.startswith('free_'):
                free_id = int(key.split('free_')[1])
                reduc = post.get('reduc_free_%s' % free_id)
                line_ids.append((0, 0, {
                    'plant_id': free_id,
                    'price': 0,
                }))
            elif key.startswith('promo_'):
                promo_id = int(key.split('promo_')[1])
                reduc = int(post.get('reduc_promo_%s' % promo_id))
                line_ids.append((0, 0, {
                    'plant_id': promo_id,
                    'price': request.env['nursery.plant'].browse(promo_id).price * ((100 - reduc) * 0.01),
                }))

        if line_ids:
            customer = request.env['nursery.customer'].find_or_create(customer_name, customer_email)
            order = request.env['nursery.order'].create({
                'customer_id': customer.id,
                'line_ids': line_ids,
            })
            return request.redirect('/plants?order_id=%s' % order.id)

        return request.redirect('/plants')

    @route('/plants/plant/<model("nursery.plant"):plant>', type='http', auth="public", website=True)
    def plant(self, plant, **post):
        values = {
            'main_object': plant,
            'company': request.env.user.company_id.sudo(),
            'plant': plant,
        }
        if post.get('order_id'):
            order_id = int(post['order_id'])
            order = request.env['nursery.order'].sudo().browse(order_id)
            values['order'] = order

        return request.render("plant_nursery.portal_plant_page", values)

    @route('/plants/plant/<model("nursery.plant"):plant>/order', type='http', auth="public", website=True)
    def plant_page_order(self, plant, **post):
        customer_name = post.get('customer_name')
        customer_email = post.get('customer_email')
        customer = request.env['nursery.customer'].sudo().find_or_create(customer_name, customer_email)
        order = request.env['nursery.order'].sudo().create({
            'customer_id': customer.id,
            'category_id': request.env.ref('plant_nursery_data.category_0').id,
            'line_ids': [(0, 0, {
                'plant_id': plant.id,
                'price': plant.price,
            })],
        })
        return request.redirect('/plants/plant/%s?order_id=%s' % (plant.id, order.id))

    # Live update
    # --------------------------------------------------

    @route(['/plant/get_random_quote'], type='json', auth="public", website=True)
    def get_plants_availability_data(self):
        plant_domain = [('number_in_stock', '>', 0)]
        plants = request.env['nursery.plant'].search(plant_domain)

        random.seed()
        promo = random.randrange(20, 80, 10)

        plant = request.env['nursery.plant'].browse([random.choice(plants.ids)])
        free = request.env['nursery.plant'].browse([random.choice(plants.ids)])

        return {
            'promo': [{
                'plant': plant.name,
                'plant_id': plant.id,
                'promo': promo,
            }],
            'free': [{
                'plant': free.name,
                'plant_id': free.id,
                'promo': 100,
            }],
        }
