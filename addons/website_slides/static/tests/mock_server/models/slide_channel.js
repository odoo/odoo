import { getKwArgs, models } from "@web/../tests/web_test_helpers";

export class SlideChannel extends models.ServerModel {
    _name = "slide.channel";
    _views = {
        form: /* xml */ `
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
            this.env["mail.activity"].action_feedback(activities.map((a) => a.id));
        }
    }

    action_refuse_access() {
        const kwargs = getKwArgs(arguments, "ids", "partner_id");
        if (kwargs.partner_id) {
            const activities = this.env["mail.activity"].search_read([
                ["request_partner_id", "=", kwargs.partner_id],
            ]);
            this.env["mail.activity"].action_feedback(activities.map((a) => a.id));
        }
    }
}
