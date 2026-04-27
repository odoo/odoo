import { models } from "@web/../tests/web_test_helpers";

export class ApprovalRequest extends models.ServerModel {
    _name = "approval.request";
    _views = {
        form: /* xml */ `
            <form>
                <chatter/>
            </form>`,
    };
}
