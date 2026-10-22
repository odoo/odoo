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

    _store_script_step_fields(res) {
        res.attr("message", (step) => ["markup", step.message]); // mock: html fields must be markup-wrapped
        res.attr("step_type");
    }
}
