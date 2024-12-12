import { models } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_VIEW_ID } from "@mail/../tests/mock_server/mock_models/constants";

export class SlideChannel extends models.ServerModel {
    _name = "slide.channel";
    _views = {
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: `
            <form>
                <chatter/>
            </form>
        `,
    };

    action_grant_access(partner_id) {
        const partner = this.env["res.partner"].browse(partner_id)[0];
        if (partner) {
            this.env["mail.activity"].search([
                ["request_partner_id", "=", partner.id],
            ]).action_feedback();
        }
    }

    action_refuse_access(partner_id) {
        const partner = this.env["res.partner"].browse(partner_id)[0];
        if (partner) {
            this.env["mail.activity"].search([
                ["request_partner_id", "=", partner.id],
            ]).action_feedback();
        }
    }
}
