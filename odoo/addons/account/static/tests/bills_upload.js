/** @odoo-module **/

import { editInput, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("Widgets", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        type: { string: "Type", type: "char"}
                    },
                    records: [
                        {
                            id: 7,
                            display_name: "first record",
                            type: "purchase",
                        },
                    ],
                    onchanges: {},
                },
            },
            views: {
                "partner,false,form": `<form>
                        <widget name="account_file_uploader"/>
                        <field name="display_name" required="1"/>
                    </form>`,
                "partner,false,list": `<tree>
                        <field name="id"/>
                        <field name="display_name"/>
                    </tree>`,
                "partner,false,search": `<search/>`,
            },
        };

        setupViewRegistries();
    });

    QUnit.module("AccountFileUploader");

    QUnit.test("widget contains context based on the record despite field not in view", async function (assert) {

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 7,
            mockRPC(route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.model, "ir.attachment", "create ir.attachment")
                    return [99];
                }
                if (args.method === "create_document_from_attachment" && args.model === "account.journal") {
                    assert.equal(args.kwargs.context.default_journal_id, 7, "create documents in correct journal");
                    assert.equal(args.kwargs.context.default_move_type, "in_invoice", "create documents with correct move type");
                    return {
                        'name': 'Generated Documents',
                        'domain': [],
                        'res_model': 'partner',
                        'type': 'ir.actions.act_window',
                        'context': {},
                        'views': [[false, "list"], [false, "form"]],
                        'view_mode': 'list, form',
                    }
                }
            },
        });
        patchWithCleanup(form.env.services.action, {
            doAction(action) {
                assert.equal(action.type, "ir.actions.act_window", "do action after documents created");
            }
        });

        assert.expect(5);
        assert.containsOnce(target, '.o_widget_account_file_uploader');
        const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
        await editInput(target, ".o_input_file", file);
        
    });

});
