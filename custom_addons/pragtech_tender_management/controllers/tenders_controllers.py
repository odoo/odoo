# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import unslug


class TendersController(http.Controller):

    @http.route(['/tender/<name>', '/tender'], type='http', auth="public", website=True)
    def tenders_bids(self, name, **post):
        _, tenders_id = unslug(name)
        values = {}

        bid_for_current_user = request.env['bids.bids'].sudo().search([('tender_id', '=', tenders_id)])
        tenderId = request.env['tenders.tenders'].sudo().search([('id', '=', tenders_id)])

        if bid_for_current_user:
            values_user = {}
            values_user.update({
                'bid_for_current_user': bid_for_current_user,
                'tenderId': tenderId
            })

            return http.request.render('pragtech_tender_management.show_bids_info', values_user)
        else:
            if tenders_id or name:
                if tenders_id:
                    partner_sudo = request.env['tenders.tenders'].sudo().browse(tenders_id)
                else:
                    partner_sudo = request.env['tenders.tenders'].sudo().search([('name', '=', name)])

                is_website_publisher = request.env['res.users'].has_group('website.group_website_publisher')
                if partner_sudo.exists() and (partner_sudo.website_published or is_website_publisher):
                    values.update({
                        'main_object': partner_sudo,
                        'tendersproducts': partner_sudo,
                        'tendersproducts_published': partner_sudo.website_published,
                        'tender_line_id': partner_sudo.tender_line_id,
                        'tender_labour_id': partner_sudo.tender_labour_id,
                        'tender_overhead_id': partner_sudo.tender_overhead_id,
                        'tender_question_ids': partner_sudo.tender_question_ids
                    })

                return http.request.render('pragtech_tender_management.show_tenders_info', values)

    @http.route(['/tenders/view/<name>', '/tender/view/'], type='http', auth="public", website=True)
    def tender_website(self, name, **kwargs):
        _, tenders_id = unslug(name)
        values = {}

        if tenders_id or name:
            if tenders_id:
                partner_sudo = request.env['tenders.tenders'].sudo().browse(tenders_id)
            else:
                partner_sudo = request.env['tenders.tenders'].sudo().search([('name', '=', name)])

            is_website_publisher = request.env['res.users'].has_group('website.group_website_publisher')
            if partner_sudo.exists() and (partner_sudo.website_published or is_website_publisher):
                values.update({
                    'main_object': partner_sudo,
                    'tendersproducts': partner_sudo,
                    'tendersproducts_published': partner_sudo.website_published,
                })

            return http.request.render('pragtech_tender_management.list_tenders', values)

    @http.route('/tenders', type='http', auth='public', website=True)
    def all_tenders_website(self, **kwargs):
        publish_done = publish_all = publish12 = request.env['tenders.tenders']

        if request.env.user and request.env.user.partner_id:
            part_name = request.env.user.partner_id.name
            publish_done = request.env['tenders.tenders'].sudo().search([('state', 'in', ['done'])])

        publish_all = request.env['tenders.tenders'].sudo().search(['&', ('website_published', '=', True), ('state', 'in', ['approve', 'in_progress'])])

        for tender in publish_done:
            publish12 += tender

        for tend in publish_all:
            publish12 += tend

        value = {}
        user = request.env['res.users'].sudo()

        if not user:
            value.update({'tendersproducts': publish12})

        return request.render("pragtech_tender_management.list_all_tenders", value)

    @http.route('/tenders/update', type='http', methods=['POST'], auth="public", website=True, csrf=False)
    def bids_details_rank(self, **kw):
        rank_value = {}

        tenderId = request.env['tenders.tenders'].search([('id', '=', int(kw.get('tender_id')))])
        if request.env.user._is_public():
            return request.render("pragtech_tender_management.logged_in_template")
        else:
            tenderId = None
            if kw.get('tender_id'):
                tenderId = request.env['tenders.tenders'].search([('id', '=', int(kw.get('tender_id')))])

            bids_obj = request.env['bids.bids']
            bids_id = bids_obj.sudo().create({
                'name_of_bidder': request.env.user.id,
                'bids_name': tenderId.name,
                'bids_street': tenderId.street,
                'bids_street2': tenderId.street2,
                'bids_city': tenderId.city,
                'bids_zip': tenderId.zip,
                'bids_start_date': tenderId.start_date,
                'bids_end_date': tenderId.end_date,
                'bids_all_total': kw.get('total_amount_duplicate')
            })

            tender_line_list = kw.get('tender_line_list')
            t_list = []

            if tender_line_list:
                for tl in tender_line_list[1:-1].split(', '):
                    t_list.append(tl)

                for tender_line in t_list:
                    tender_line_obj = request.env['tenders.tenders.line'].search([('id', '=', tender_line)])
                    bids_line_obj = request.env['bids.bids.line']
                    mat_vals = {}
                    mat_vals.update({
                        'bids_product_id': tender_line_obj.product_id.id,
                        'bids_description': tender_line_obj.line_description,
                        'bids_product_uom_qty': tender_line_obj.product_uom_qty,
                        'mat_last_price': tender_line_obj.material_last_price,
                        'mat_note': kw.get('material_note-' + str(tender_line)),
                        'mat_amount': kw.get('material_amount_duplicate-' + str(tender_line)),
                        'mat_your_price': kw.get('material_your_price-' + str(tender_line)),
                        'bids_product_uom': tender_line_obj.product_uom.id,
                        'line_id': bids_id.id
                    })

                    bids_line_obj.create(mat_vals)

            tender_labour_list = kw.get('tender_labour_list')
            tl_list = []
            tender_overhead_list = []
            if tender_labour_list:
                for tlabour in tender_labour_list[1:-1].split(', '):
                    tl_list.append(tlabour)

                for tender_labour in tl_list:
                    tender_labour_obj = request.env['tenders.labour'].search([('id', '=', tender_labour)])
                    bids_line_obj = request.env['bids.labour']
                    labour_vals = {}
                    labour_vals.update({
                        'labour_id': tender_labour_obj.tender_labour_labour_id.id,
                        'bids_labour_description': tender_labour_obj.labour_description,
                        'bids_labour_qty': tender_labour_obj.labour_qty,
                        'bids_labour_last_price': tender_labour_obj.labour_last_price,
                        'bids_labour_note': kw.get('labour_note-' + str(tender_labour_obj.id)),
                        'bids_labour_amount': kw.get('labour_amount_duplicate-' + str(tender_labour_obj.id)),
                        'bids_labour_product_uom': tender_labour_obj.product_uom.id,
                        'bids_labour_your_price': kw.get('labour_your_price-' + str(tender_labour_obj.id)),
                        'bids_labour_id': bids_id.id
                    })

                    bids_line_obj.create(labour_vals)
                    tender_overhead_list = kw.get('tender_overhead_list')

            to_list = []
            if tender_overhead_list:
                for toverhead in tender_overhead_list[1:-1].split(', '):
                    to_list.append(toverhead)

                for tender_overhead in to_list:
                    tender_overhead_obj = request.env['tenders.overhead'].search([('id', '=', tender_overhead)])
                    bids_overhead_obj = request.env['bids.overhead']
                    overhead_vals = {}
                    overhead_vals.update({
                        'overhead_id': tender_overhead_obj.tender_overhead_overhead_id.id,
                        'bids_overhead_description': tender_overhead_obj.overhead_description,
                        'bids_overhead_qty': tender_overhead_obj.overhead_qty,
                        'bids_overhead_last_price': tender_overhead_obj.overhead_last_price,
                        'bids_overhead_note': kw.get('overhead_note-' + str(tender_overhead_obj.id)),
                        'bids_overhead_amount': kw.get('overhead_amount_duplicate-' + str(tender_overhead_obj.id)),
                        'bids_overhead_product_uom': tender_overhead_obj.product_uom.id,
                        'bids_overhead_your_price': kw.get('overhead_your_price-' + str(tender_overhead_obj.id)),
                        'bids_overhead_id': bids_id.id
                    })

                    bids_overhead_obj.create(overhead_vals)

            questionnaire_list = kw.get('questionnaire_list')
            question_list = []
            if questionnaire_list:
                for tquestions in questionnaire_list[1:-1].split(', '):
                    question_list.append(tquestions)

                for tender_question in question_list:
                    tender_question_obj = request.env['question.question'].search([('id', '=', tender_question)])
                    bids_question_obj = request.env['bids.questions']
                    question_vals = {}
                    question_vals.update({
                        'bids_id': bids_id.id,
                        'answer': kw.get('answer-' + str(tender_question_obj.tender_question_id.id)),
                        'question': tender_question_obj.tender_question_id.name,
                    })
                    bids_question_obj.create(question_vals)

            if bids_id:
                bids_id.bids_state_id = tenderId.state_id
                bids_id.bids_country_id = tenderId.country_id
                bids_id.bids_user_id = tenderId.user_id
                bids_id.tender_id = tenderId.id,
                rank_bid_id = request.env['bids.bids'].search([('tender_id', '=', bids_id.tender_id.id)])
                rank = 0
                tmp_dict = {}
                sorted_dict = []

                for bid_id in rank_bid_id:
                    tmp_dict.update({bid_id.id: bid_id.bids_all_total})

                sorted_dict = sorted(tmp_dict.items(), key=lambda kv: (kv[1], kv[0]))
                for ele in sorted_dict:
                    rank += 1
                    if ele[0] == bids_id.id:
                        break

                rank_value.update({
                    'rank': rank
                })

                AllbidIdRank = request.env['bids.bids'].search([('tender_id', '=', bids_id.tender_id.id), ('bids_top_rank', '>=', rank)])
                for bidIdRank in AllbidIdRank:
                    bidIdRank.bids_top_rank = bidIdRank.bids_top_rank + 1

                bids_id.bids_top_rank = rank

        return request.render("pragtech_tender_management.rank_template", rank_value)

