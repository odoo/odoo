import { DiscussChannel } from "@mail/../tests/mock_server/mock_models/discuss_channel";

import { markup } from "@odoo/owl";

import { getKwArgs, makeKwArgs } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

/** @type {import("mock_models").DiscussChannel} */
const discussChannelPatch = {
    execute_command_lead() {
        const { ids, body } = getKwArgs(arguments, "ids", "body");
        const [channel] = this.browse(ids);
        if (body.trim() === "/lead") {
            this._bus_send_transient_message(
                channel.id,
                "Create a new lead with: <pre>/lead <i>lead title</i></pre>"
            );
            return;
        }
        const [partner] = this.env["res.partner"].browse(this.env.user.partner_id);
        const lead = this._convert_visitor_to_lead(ids, partner, body);
        const leadLink = markup`<a href="#" data-oe-model="crm.lead" data-oe-id="${lead.id}">${lead.name}</a>`;
        this.message_post(
            channel.id,
            makeKwArgs({
                body: String(
                    markup`<div class="o_mail_notification" data-oe-type="create-lead">created a new lead: ${leadLink}</div>`
                ),
                message_type: "notification",
            })
        );
    },

    _convert_visitor_to_lead(ids, partner, key) {
        const CrmLead = this.env["crm.lead"];
        const leadId = CrmLead.create(this._prepare_lead_create_values(ids, partner, key));
        return CrmLead.browse(leadId)[0];
    },

    _prepare_lead_create_values(ids, partner, key) {
        const [channel] = this.browse(ids);
        return {
            description: this._get_channel_history(ids),
            name: key.slice(5).trim(),
            origin_channel_id: channel.id,
            partner_id: false,
            referred: partner.name,
            team_id: false,
            user_id: false,
        };
    },

    _types_allowing_lead_command() {
        return [];
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
