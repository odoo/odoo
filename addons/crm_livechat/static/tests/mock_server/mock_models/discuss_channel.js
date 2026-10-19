import { DiscussChannel } from "@im_livechat/../tests/mock_server/mock_models/discuss_channel";

import { getKwArgs, makeKwArgs } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

const discussChannelPatch = {
    execute_command_lead() {
        const kwargs = getKwArgs(arguments, "ids", "body");
        const ids = kwargs.ids;
        const body = kwargs.body;

        const leadName = body.substring("/lead".length).trim();
        const leadId = this.env["crm.lead"].create({ name: leadName });
        this.message_post(
            ids[0],
            makeKwArgs({
                body: `<div class="o_mail_notification">created a new lead: <a href="#" data-oe-model="crm.lead" data-oe-id="${leadId}">${leadName}</a></div>`,
                subtype_xmlid: "mail.mt_comment",
            })
        );
        return true;
    },

    _store_livechat_extra_fields(res) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        super._store_livechat_extra_fields(...arguments);
        res.many("livechat_customer_partner_ids", (res) => res.many("opportunity_ids", ["name"]), {
            only_data: true,
            value: (channel) => ResPartner.browse(this._livechat_customer_partner_ids(channel)),
        });
    },
};

patch(DiscussChannel.prototype, discussChannelPatch);
