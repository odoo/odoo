/** @odoo-module **/

import { getFixture, click } from "@web/../tests/helpers/utils";

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData

QUnit.module('widgets', ()=> {
    QUnit.module('PopoverWidget', hooks => {
        hooks.beforeEach(()=>{
            target = getFixture();
            setupViewRegistries();
            serverData = {
                models: {
                    partner: {
                        fields: {
                            json_data: {string: " ", type: "char"},
                        },
                        records: [
                            {id:1, json_data:'{"color": "text-danger", "msg": "var that = self // why not?", "title": "JS Master"}'}
                        ]
                    }
                }
            };

        });

        QUnit.test('Test creation/usage form popover widget', async assert => {
            assert.expect(5);
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="json_data" widget="popover_widget"/>
                    </form>`,
                resId: 1,
            });
            assert.containsNone(target, 'div.popover', "Shouldn't have a popover container in DOM");
            assert.containsOnce(target, 'a.fa.fa-info-circle.text-danger', "Should have a popover icon/button in red");
            await click(target, 'a.fa.fa-info-circle.text-danger');
            assert.containsOnce(target, 'div.popover', "Should have a popover icon/button in red");
            assert.strictEqual(
                target.querySelector("div.popover").innerHTML.includes("var that = self // why not?"),
                true,
                "The message should be in DOM"
            );
            assert.strictEqual(
                target.querySelector("div.popover").innerHTML.includes("JS Master"),
                true,
                "The title should be in DOM"
            );

        });
    });
});
