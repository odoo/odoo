import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_VIEW_ID } from "@mail/../tests/mock_server/mock_models/constants";

export class ResFake extends mailModels.ResFake {
    _views = {
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: /* xml */ `
            <form>
                <field name="duration" widget="mrp_timer" readonly="1"/>
            </form>`,
    }
    duration = fields.Float({ string: "duration" });
}
