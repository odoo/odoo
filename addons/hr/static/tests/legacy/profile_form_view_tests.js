/** @odoo-module **/

import { clickSave, editInput, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        lang: { string: "Lang", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Aline",
                            lang: "fr",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("EmployeeProfileController");

    QUnit.test(
        "editing the 'lang' field and saving it triggers a 'reload_context'",
        async function (assert) {
            const form = await makeView({
                type: "form",
                resModel: "user",
                serverData,
                arch: `
                <form js_class="hr_employee_profile_form">
                    <field name="name"/>
                    <field name="lang"/>
                </form>`,
                resId: 1,
            });

            patchWithCleanup(form.env.services.action, {
                doAction: (action, options) => {
                    assert.step(action);
                },
            });

            await editInput(target, "[name='name'] input", "John");
            await clickSave(target);
            assert.verifySteps([]);

            await editInput(target, "[name='lang'] input", "En");
            await clickSave(target);
            assert.verifySteps(["reload_context"]);
        }
    );
});
