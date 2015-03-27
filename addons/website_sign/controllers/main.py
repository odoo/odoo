# -*- coding: utf-8 -*-
from openerp import http, _

from openerp.addons.web.controllers.main import content_disposition
import time, mimetypes, base64, os, datetime, uuid, re

class website_sign(http.Controller):

    def __message_post(self, message, signature_request_id, partner, type='comment', subtype=False):
        model = http.request.env['signature.request'].with_context(notify_author=True)

        user = None
        if partner:
            user = http.request.env['res.users'].sudo().search([('partner_id', '=', partner.id)]) or None
        if not user:
            model = model.sudo()
            message = "<b>%s</b> %s" % (partner.name if partner else "Public User", message)
        else:
            model = model.sudo(user.id)

        return model.browse(signature_request_id).message_post(
            body=message,
            type=type,
            subtype=subtype
        )

    @http.route(['/sign'], type="http", auth="user", website=True)
    def sign_dashboard(self, **post):
        values = {
            'templates': http.request.env['signature.request.template'].search([]).sorted(key=(lambda r: r.attachment_id.name)),
            'signature_requests': http.request.env['signature.request'].search([]).sorted(key=(lambda r: r.message_ids[0].create_date), reverse=True),
            'toggles': {'favorite': http.request.session.website_sign_favorite, 'archive': http.request.session.website_sign_archive}
        }

        return http.request.render('website_sign.dashboard', values)

    @http.route(['/sign/set_toggles'], type="json", auth="user", website=True)
    def set_toggles(self, object=None, value=None, **post): # TODO is it correct use of session variables?
        if object == 'archive':
            http.request.session.website_sign_archive = bool(value)
        elif object == 'favorite':
            http.request.session.website_sign_favorite = bool(value)

    @http.route(['/sign/template/<int:template_id>'], type="http", auth="user", website=True)
    def custom_template(self, template_id, **post):
        template = http.request.env['signature.request.template'].sudo().search([('id', '=', template_id)])
        if not template:
            return http.request.not_found()

        user = ''.join([c[0] for c in http.request.env.user.partner_id.name.split(' ')])

        values = {
            'signature_request_template': template,
            'signature_items': template.signature_item_ids,
            'signature_item_parties': http.request.env['signature.item.party'].search([]),
            'signature_item_types': http.request.env['signature.item.type'].search([]),
            'default_reference': "-%s" % user,
            'has_signature_requests': (len(template.signature_request_ids) > 0),
            'isPDF': (template.attachment_id.mimetype.find('pdf') > -1)
        }
        return http.request.render('website_sign.items_edit', values)

    @http.route(['/sign/new_template'], type='json', auth='user', website=True)
    def create_template(self, name=None, dataURL=None, **post):
        mimetype = dataURL[dataURL.find(':')+1:dataURL.find(',')]
        datas = dataURL[dataURL.find(',')+1:]
        attachment = http.request.env['ir.attachment'].create({'name': name, 'datas_fname': name, 'datas': datas, 'mimetype': mimetype})
        template = http.request.env['signature.request.template'].create({'attachment_id': attachment.id, 'favorited_ids': [(4, http.request.env.user.id)]})
        return {'template': template.id, 'attachment': attachment.id}

    @http.route(['/sign/update_template/<int:template_id>/<action>'], type='json', auth='user', website=True)
    def update_template(self, template_id=None, action=None, signature_items=None, name=None, **post):
        template = http.request.env['signature.request.template'].sudo().search([('id', '=', template_id)])
        if not template:
            return http.request.not_found()

        if action == 'duplicate':
            new_attachment = template.attachment_id.copy()
            r = re.compile(' \(v(\d+)\)$')
            m = r.search(name)
            v = str(int(m.group(1))+1) if m else "2"
            index = m.start() if m else len(name)
            new_attachment.name = name[:index] + " (v" + v + ")"

            template = http.request.env['signature.request.template'].sudo().create({
                'attachment_id': new_attachment.id,
                'favorited_ids': [(4, http.request.env.user.id)]
            })
        elif name:
            template.attachment_id.name = name

        item_ids = filter(lambda a: a > 0, map(lambda itemId: int(itemId), signature_items.keys()))
        template.signature_item_ids.filtered(lambda r: r.id not in item_ids).unlink()
        for item in template.signature_item_ids:
            item.write(signature_items.pop(str(item.id)))
        for item in signature_items.values():
            item['template_id'] = template.id
            http.request.env['signature.item'].create(item)

        template.share_link = None

        return template.id

    @http.route(['/sign/add_signature_item_party'], type='json', auth='user', website=True)
    def add_signature_item_party(self, name, **post):
        party = http.request.env['signature.item.party'].search([('name', '=', name)])
        if party:
            return party.id
        return http.request.env['signature.item.party'].create({'name': name}).id

    @http.route(['/sign/create_document/<int:id>'], type='json', auth="user", website=True)
    def create_document(self, id=None, signers=None, followers=None, reference=None, subject=None, message=None, send=None, **post):
        signature_request = http.request.env['signature.request'].create({'template_id': id, 'reference': reference, 'follower_ids': [(6, 0, followers)], 'favorited_ids': [(4, http.request.env.user.id)]})
        signature_request.set_signers(signers)
        if send:
            signature_request.action_sent(subject, message)
        return signature_request.id

    @http.route(["/sign/document/<int:id>"], type='http', auth="user", website=True)
    def sign_document_user(self, id, message=False, **post):
        return self.sign_document_public(id, None, message)

    @http.route(["/sign/document/<int:id>/<token>"], type='http', auth="public", website=True)
    def sign_document_public(self, id, token, message=False, **post):
        signature_request = http.request.env['signature.request'].sudo().search([('id', '=', id)])
        if not signature_request:
            if token:
                return http.request.render('website_sign.deleted_sign_request')
            else:
                return http.request.not_found()

        current_request_item = None
        if token:
            current_request_item = signature_request.request_item_ids.filtered(lambda r: r.access_token == token)
            if not current_request_item and signature_request.access_token != token:
                return http.request.render('website_sign.deleted_sign_request')
        elif signature_request.create_uid.id != http.request.env.user.id:
            return http.request.not_found()

        signature_item_types = http.request.env['signature.item.type'].sudo().search_read([])
        if current_request_item:
            for item_type in signature_item_types:
                if item_type['auto_field']:
                    fields = item_type['auto_field'].split('.')
                    auto_field = current_request_item.partner_id
                    for field in fields:
                        if auto_field and field in auto_field:
                            auto_field = auto_field[field]
                        else:
                            auto_field = ""
                            break
                    item_type['auto_field'] = auto_field

        sr_values = http.request.env['signature.item.value'].search([('signature_request_id', '=', signature_request.id)])
        item_values = {}
        for value in sr_values:
            item_values[value.signature_item_id.id] = value.value

        values = {
            'signature_request': signature_request,
            'current_request_item': current_request_item,
            'token': token,
            'messages': signature_request.message_ids,
            'message': message and int(message) or False,
            'isPDF': (signature_request.template_id.attachment_id.mimetype.find('pdf') > -1),
            'hasItems': len(signature_request.template_id.signature_item_ids) > 0,
            'signature_items': signature_request.template_id.signature_item_ids,
            'item_values': item_values,
            'role': current_request_item.role_id.id if current_request_item else 0,
            'readonly': not (current_request_item and current_request_item.state == 'sent'),
            'signature_item_types': signature_item_types,
        }

        return http.request.render('website_sign.doc_sign', values)

    @http.route(['/sign/signed/<int:id>/<token>'], type='json', auth="public", website=True)
    def signed(self, id=None, token=None, sign=None, **post):
        request_item = http.request.env['signature.request.item'].sudo().search([('signature_request_id', '=', id), ('access_token', '=', token)], limit=1)
        if request_item:
            self.__message_post(_('Signed !'), id, request_item.partner_id, type='notification', subtype='mt_comment')
            request_item.sudo().sign(sign)

        return {'id': id, 'token': token}

    @http.route(['/sign/document/<int:id>/<token>/note'], type='http', auth="public", website=True)
    def post_note(self, id, token, **post):
        request_item = http.request.env['signature.request.item'].sudo().search([('signature_request_id', '=', id), ('access_token', '=', token)], limit=1)
        if not request_item:
            return http.request.not_found()

        message = post.get('comment')
        if message:
            self.__message_post(message, id, request_item.partner_id, type='comment', subtype='mt_comment')
            return http.request.redirect("/sign/document/%s/%s?message=1" % (id, token))
        else:
            return http.request.redirect("/sign/document/%s/%s" % (id, token))

    @http.route(['/sign/get_fonts'], type='json', auth='public', website=True)
    def get_fonts(self, **post):
        fonts = []
        fonts_directory = os.path.dirname(os.path.abspath(__file__)) + '/../static/src/font'
        font_filenames = sorted(os.listdir(fonts_directory))

        for filename in font_filenames:
            font_file = open(fonts_directory + '/' + filename, 'r')
            font = base64.b64encode(font_file.read())
            fonts.append([filename[:-len('.ttf')], font])
        return fonts

    @http.route(['/sign/download/<int:id>/<token>/<type>'], type='http', auth='public', website=True)
    def download_document(self, id, token, type, **post):
        signature_request = http.request.env['signature.request'].sudo().search([('id', '=', id), ('access_token', '=', token)])
        if not signature_request:
            return http.request.not_found()

        document = None
        if type == "origin":
            document = signature_request.template_id.attachment_id.datas
        elif type == "completed":
            document = signature_request.completed_document

        if not document:
            return http.request.not_found()

        filecontent = base64.b64decode(document)
        filename = signature_request.reference
        if filename != signature_request.template_id.attachment_id.datas_fname:
            filename += signature_request.template_id.attachment_id.datas_fname[signature_request.template_id.attachment_id.datas_fname.rfind('.'):]
        content_type = mimetypes.guess_type(filename)
        return http.request.make_response(
            filecontent,
            headers = [
                ('Content-Type', content_type[0] or 'application/octet-stream'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )

    @http.route(['/sign/archive/<object>/<int:id>'], type='json', auth='user', website=True)
    def archive(self, object, id, value=None, **post):
        if object == 'template':
            http.request.env['signature.request.template'].browse(id).archived = value
        elif object == 'document':
            http.request.env['signature.request'].browse(id).archived = value
        return value

    @http.route(['/sign/favorite/<object>/<int:id>'], type='json', auth='user', website=True)
    def favorite(self, object, id, value=None, **post):
        model = None
        if object == 'template':
            model = http.request.env['signature.request.template']
        elif object == 'document':
            model = http.request.env['signature.request']

        model.browse(id).write({'favorited_ids': [((4 if value else 3), http.request.env.user.id)]})
        return value

    @http.route(['/sign/get_partners'], type='json', auth='user', website=True)
    def get_partners(self, **post):
        return http.request.env['res.partner'].search_read([('email', '!=', '')], ['name', 'email'])

    @http.route(['/sign/new_partner'], type='json', auth='user', website=True)
    def new_partner(self, name=None, mail=None, **post):
        existing_partner = http.request.env['res.partner'].search([('email', '=', mail)], limit=1)
        if existing_partner:
            return existing_partner.id
        else:
            return http.request.env['res.partner'].create({'name': name, 'email': mail}).id

    @http.route(['/sign/cancel/<int:id>'], type='json', auth='user', website=True)
    def cancel_request(self, id, **post):
        return http.request.env['signature.request'].browse(id).action_canceled()

    @http.route(['/sign/share/<int:id>'], type='json', auth='user', website=True)
    def share(self, id, **post):
        template = http.request.env['signature.request.template'].browse(id)
        if len(template.signature_item_ids.mapped('responsible_id')) > 1:
            return False

        if not template.share_link:
            template.share_link = str(uuid.uuid4())
        return template.share_link

    @http.route(['/sign/<link>'], type='http', auth='public', website=True)
    def share_link(self, link, **post):
        template = http.request.env['signature.request.template'].sudo().search([('share_link', '=', link)], limit=1)
        if not template:
            return http.request.not_found()

        signature_request = http.request.env['signature.request'].sudo().create({
            'template_id': template.id,
            'reference': "%s-public" % template.attachment_id.name
        })

        request_item = http.request.env['signature.request.item'].sudo().create({'signature_request_id': signature_request.id, 'role_id': template.signature_item_ids.mapped('responsible_id').id})
        signature_request.action_sent()

        return http.request.redirect('/sign/document/%s/%s' % (signature_request.id, request_item.access_token))

    @http.route(['/sign/send_public/<int:id>/<token>'], type='json', auth='public', website=True)
    def make_public_user(self, id, token, name=None, mail=None, **post):
        signature_request = http.request.env['signature.request'].sudo().search([('id', '=', id), ('access_token', '=', token)])
        if not signature_request or len(signature_request.request_item_ids) != 1 or signature_request.request_item_ids.partner_id:
            return http.request.not_found()

        partner_model = http.request.env['res.partner'].sudo()
        partner = partner_model.search([('email', '=', mail)], limit=1)
        if not partner:
            partner = partner_model.create({'name': name, 'email': mail})

        signature_request.request_item_ids[0].write({'partner_id': partner.id})

    @http.route(['/sign/save_location/<int:id>/<token>'], type='json', auth='public', website=True)
    def save_location(self, id, token, latitude=None, longitude=None, **post):
        signature_request_item = http.request.env['signature.request.item'].sudo().search([('signature_request_id', '=', id), ('access_token', '=', token)], limit=1)
        if not signature_request_item:
            return http.request.not_found()

        signature_request_item.write({'latitude': latitude, 'longitude': longitude})

    @http.route(['/sign/resend_access'], type='json', auth='user', website=True)
    def resend_access(self, id=None, **post):
        http.request.env['signature.request.item'].browse(id).send_signature_accesses()

    @http.route(['/sign/add_followers/<int:id>'], type='json', auth='user', website=True)
    def add_followers(self, id, followers=None, **post):
        signature_request = http.request.env['signature.request'].browse(id)
        old_followers = set(signature_request.follower_ids.mapped('id'))
        signature_request.write({'follower_ids': [(6, 0, set(followers) | old_followers)]})
        signature_request.send_follower_accesses(http.request.env['res.partner'].browse(followers))
        return signature_request.id
