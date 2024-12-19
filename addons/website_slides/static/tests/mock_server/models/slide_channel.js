import { getKwArgs, models } from "@web/../tests/web_test_helpers";
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

    action_grant_access() {
        const kwargs = getKwArgs(arguments, "ids", "partner_id");
        if (kwargs.partner_id) {
            const activities = this.env["mail.activity"].search_read([
                ["request_partner_id", "=", kwargs.partner_id],
            ]);
            this.env["mail.activity"].action_feedback(activities.map(a => a.id));
        }
    }

    action_refuse_access() {
        const kwargs = getKwArgs(arguments, "ids", "partner_id");
        if (kwargs.partner_id) {
            const activities = this.env["mail.activity"].search_read([
                ["request_partner_id", "=", kwargs.partner_id],
            ]);
            this.env["mail.activity"].action_feedback(activities.map(a => a.id));
        }
    }
}
