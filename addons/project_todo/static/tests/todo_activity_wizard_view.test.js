import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { queryFirst, click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { ActivityMenu } from "@mail/core/web/activity_menu";
import { triggerHotkey } from "@mail/../tests/mail_test_helpers";

import { defineTodoModels } from "./todo_test_helpers";
import { MailActivityTodoCreate } from "./mock_server/mock_models/mail_activity_todo_create";

describe.current.tags("desktop");
defineTodoModels();

beforeEach(() => {
    MailActivityTodoCreate._views = {
        form: `
            <form js_class="todo_activity_wizard">
                <group>
                    <field name="summary" placeholder="Reminder to..." required="1"/>
                    <field name="date_deadline"/>
                    <field name="user_id" widget="many2one_avatar_user" options="{'no_open': 1}"/>
                </group>
                <footer>
                    <button class="btn btn-primary" type="object" name="create_todo_activity" close="1">Add To-Do</button>
                    <button class="btn btn-secondary" special="cancel" close="1">Discard</button>
                </footer>
            </form>`,
    };
});

test("Check that todo_activity_wizard view focuses on the first element", async () => {
    await mountWithCleanup(ActivityMenu);

    // Open todo activity wizard through the command palette tool
    await triggerHotkey("control+k");
    await animationFrame();
    await click(`.o_command:contains("Add a To-Do")`);
    await animationFrame();
    expect(queryFirst("div.o_field_widget input")).toBeFocused({
        message: "The first element should be focused",
    });
});
