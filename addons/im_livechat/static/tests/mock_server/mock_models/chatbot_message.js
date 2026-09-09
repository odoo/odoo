import { fields, models } from "@web/../tests/web_test_helpers";

export class ChatbotMessage extends models.ServerModel {
    _name = "chatbot.message";

    discuss_channel_id = fields.Many2one({ relation: "discuss.channel" });
    script_step_id = fields.Many2one({ relation: "chatbot.script.step" });
    user_script_answer_id = fields.Many2one({ relation: "chatbot.script.answer" });
    user_raw_answer = fields.Html({ sanitize: true });

    _store_chatbot_message_fields(res) {
        /** @type {import("mock_models").ChatbotScriptAnswer} */
        const ChatbotScriptAnswer = this.env["chatbot.script.answer"];
        /** @type {import("mock_models").ChatbotScriptStep} */
        const ChatbotScriptStep = this.env["chatbot.script.step"];

        res.one("script_step_id", ["step_type"], {
            value: (message) => ChatbotScriptStep.browse(message.script_step_id),
        });
        res.one("user_script_answer_id", ["name"], {
            value: (message) => ChatbotScriptAnswer.browse(message.user_script_answer_id),
        });
        res.attr(
            "user_raw_answer",
            (message) => ["markup", message.user_raw_answer] // mock: html fields must be markup-wrapped
        );
    }
}
