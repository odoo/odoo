import { fields, models } from "@web/../tests/web_test_helpers";

export class ChatbotScriptStep extends models.ServerModel {
    _name = "chatbot.script.step";

    step_type = fields.Selection({
        selection: [
            ["free_input_multi", "Free Input (Multi-Line)"],
            ["free_input_single", "Free Input"],
            ["question_email", "Email"],
            ["question_phone", "Phone"],
            ["question_selection", "Question"],
            ["text", "Text"],
        ],
    });
}
