import { models } from "@web/../tests/web_test_helpers";

export class ChatbotScriptStep extends models.ServerModel {
    _name = "chatbot.script.step";

    get _to_store_defaults() {
        return ["message", "step_type"];
    }
}
