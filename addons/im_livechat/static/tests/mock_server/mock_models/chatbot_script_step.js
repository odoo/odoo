import { models } from "@web/../tests/web_test_helpers";

export class ChatbotScriptStep extends models.ServerModel {
    _name = "chatbot.script.step";

    _store_script_step_fields(res) {
        res.extend(["message", "step_type"]);
    }
}
