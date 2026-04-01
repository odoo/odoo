import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResFake extends mailModels.ResFake {
    duration = fields.Float({ string: "duration" });

    _views = {
        form: /* xml */ `
            <form>
                <field name="duration" widget="mrp_timer" readonly="1"/>
            </form>`,
    };
}
