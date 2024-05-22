import { models } from "@web/../tests/web_test_helpers";

export class MailActivityTodoCreate extends models.ServerModel {
    _name = "mail.activity.todo.create";

    _views = {
        form: `
            <form js_class="todo_activity_wizard">
                <group>
                    <field name="summary" placeholder="Reminder to..." required="1"/>
                    <field name="date_deadline"/>
                    <field name="user_id" widget="many2one_avatar_user" options="{'no_open': 1}"/>
                </group>
                <field name="note" class="oe-bordered-editor" placeholder="Add details about your to-do..."/>
                <footer>
                    <button class="btn btn-primary" type="object" name="create_todo_activity" close="1">Add To-Do</button>
                    <button class="btn btn-secondary" special="cancel" close="1">Discard</button>
                </footer>
            </form>`,
    }
}
