/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        stage_id: { string: "Stage", type: "many2one", relation: "stage_model" },
                        duration_tracking: {
                            string: "Time per stage",
                            type: "char",
                            default: "{}",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            stage_id: 30,
                            // 7 days, 30 minutes - 3 hours - 2 days, 5 hours
                            duration_tracking: {
                                10: 7 * 24 * 60 * 60 + 30 * 60,
                                20: 3 * 60 * 60,
                                40: 24 * 2 * 60 * 60 + 5 * 60 * 60,
                            },
                        },
                    ],
                },
                stage_model: {
                    fields: {
                        name: { string: "Stage Name", type: "char" },
                    },
                    records: [
                        {
                            id: 10,
                            display_name: "New",
                        },
                        {
                            id: 20,
                            display_name: "Qualified",
                        },
                        {
                            id: 30,
                            display_name: "Proposition",
                        },
                        {
                            id: 40,
                            display_name: "Won",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("StatusBarDurationField");

    QUnit.test("StatusBarDurationField in a form view", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                    <form>
                        <header>
                            <field name="stage_id" widget="statusbar_duration" />
                        </header>
                    </form>`,
            resId: 1,
        });

        // Check that time is put in the stages
        const firstButton = target.querySelector("button[data-value='10'");
        assert.strictEqual(firstButton.innerText, "New7d");
        assert.strictEqual(firstButton.querySelectorAll("span")[1].title, "7 days, 30 minutes");

        const secondButton = target.querySelector("button[data-value='20']");
        assert.strictEqual(secondButton.innerText, "Qualified3h");
        assert.strictEqual(secondButton.querySelectorAll("span")[1].title, "3 hours");

        const thirdButton = target.querySelector("button[data-value='30']");
        assert.strictEqual(thirdButton.innerText, "Proposition");
        assert.strictEqual(thirdButton.title, "");

        const fourthButton = target.querySelector("button[data-value='40']");
        assert.strictEqual(fourthButton.innerText, "Won2d");
        assert.strictEqual(fourthButton.querySelectorAll("span")[1].title, "2 days, 5 hours");
    });
});
