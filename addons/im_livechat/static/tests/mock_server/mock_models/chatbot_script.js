import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class ChatbotScript extends models.ServerModel {
    _name = "chatbot.script";

    get _to_store_defaults() {
        return [
            mailDataHelpers.Store.one("operator_partner_id", makeKwArgs({ fields: ["name"] })),
            "title",
        ];
    }

    _get_welcome_steps(id) {
        const steps = this.env["chatbot.script.step"]
            ._filter([["chatbot_script_id", "=", id]])
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0) || a.id - b.id);
        const welcomeSteps = [];
        for (const step of steps) {
            welcomeSteps.push(step);
            if (step.step_type !== "text") {
                break;
            }
        }
        return welcomeSteps;
    }
}
