import { fields, models } from "@web/../tests/web_test_helpers";

export class MailActivityTodoCreate extends models.Model {
    _name = "mail.activity.todo.create";

    summary = fields.Char();
    date_deadline = fields.Date({ string: "Due Date", default: "2023-10-10" });
    user_id = fields.Many2one({ string: "Assigned to", relation: "res.users" });
    note = fields.Html({ sanitize_style: true });
}
