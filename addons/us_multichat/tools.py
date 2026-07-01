from odoo import SUPERUSER_ID
LOG_DEBUG = "debug"


# Wrapped functions to safely pass as eval context.
# Mostly for Sync Studio
def get_multi_chat_eval_context(env, channel_type, eval_context):
    get_link = eval_context["get_link"]
    search_links = eval_context["search_links"]

    odoobot_id = env.user.browse(SUPERUSER_ID).partner_id.id
    log = eval_context["log"]

    def get_channel(relation, ref, channel_name, partner_ids, bot_id, avatar=None):
        links = get_link(relation, ref, bot_id)
        is_new = False
        if not links:
            is_new = True
            vals = env["mail.channel"]._prepare_multi_livechat_channel_vals(
                channel_type, channel_name, partner_ids, avatar
            )
            channel = env["mail.channel"].create(vals)
            channel._broadcast(partner_ids)
            links = [channel.set_link(relation, ref, bot_id)]
            log("Channel created: %s" % channel)
        return [link.odoo for link in links], is_new

    def get_partner(relation, ref, bot_id, callback_vals, callback_kwargs):
        link = get_link(relation, ref, bot_id)
        is_new = False
        if not link:
            is_new = True
            vals = callback_vals(**callback_kwargs)
            partner = env["res.partner"].sudo().create(vals)
            link = partner.set_link(relation, ref, bot_id)
            log("Partner created: %s" % partner)
        return link.odoo, is_new

    def get_thread(
        relation, ref, callback_vals, callback_kwargs, model, record_message, bot_id
    ):
        link = get_link(relation, ref, bot_id)
        is_new = False
        if not link:
            is_new = True
            vals = callback_vals(**callback_kwargs)
            if model == "crm.lead":
                vals["company_id"] = eval_context["bot"].company_id.id
            record = env[model].with_user(odoobot_id).create(vals)
            link = record.set_link(relation, ref, bot_id)
            if record_message:
                record.sudo().message_post(
                    body=record_message,
                    author_id=odoobot_id,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )
            log("Record created: %s" % record)
        return link.odoo, is_new

    def get_channel_url(channel):
        return "/web#action=%s&active_id=mail.channel_%s" % (
            env.ref("mail.action_discuss").id,
            channel.id,
        )

    def get_record_url(record):
        return "/web#id=%s&model=%s" % (
            record.id,
            record._name,
        )

    def message_post(record, message, author=None, external_messenger_id='',document_message_id=None, **kwargs):
        log("Post message to %s:\n%s" % (record, message), LOG_DEBUG)
        if document_message_id:
            record_document = env[document_message_id.model].browse(document_message_id.res_id)
            if 'name' not in record_document._fields:
                if 'title' not in record_document._fields:
                    name = str(record_document.id)
                else:
                    name = record_document.title
            else:
                name = record_document.name
            message += """<br/><br/><b><a href="/web#id=%s&model=%s">Link on model %s "%s". </a></b>""" % (document_message_id.res_id, document_message_id.model, record_document._description, name)
        doc_id = document_message_id.id if document_message_id else None
        msg = record.sudo().message_post(
            body=message,
            author_id=author or odoobot_id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            external_messenger_id=external_messenger_id,
            document_message_id=doc_id,
            **kwargs,
        )
        if record and record._name == 'mail.channel':
            if msg:
                values = []
                for channel_member in record.channel_member_ids:
                    values.append((4, channel_member.partner_id.id))
                if (4, author) in values:
                    values.remove((4, author))
                msg.write({'partner_ids': values})
        return msg

    return {
        "get_channel": get_channel,
        "get_partner": get_partner,
        "get_thread": get_thread,
        "get_record_url": get_record_url,
        "get_channel_url": get_channel_url,
        "message_post": message_post,
        "channel_type": channel_type,
        "odoobot_id": odoobot_id,
    }

