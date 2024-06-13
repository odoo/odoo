/* @odoo-module */

import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, getFixture, triggerHotkey } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch(["mail.activity.todo.create"]);

let serverData;
let target;

QUnit.module("todoActivityWizardView Tests", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            views: {
                "mail.activity.todo.create,false,form": `
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
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Check that todo_activity_wizard view focuses on the first element", async function (assert) {
        assert.expect(1);
        await start({
            serverData,
        });
        // Open todo activity wizard through the command palette tool
        await triggerHotkey("control+k");
        await click(target.querySelector("span[title='Add a To-Do']"));
        assert.strictEqual(
            document.activeElement,
            target.querySelector("div.o_field_widget input"),
            "The first element should be focused"
        );
    });
});
