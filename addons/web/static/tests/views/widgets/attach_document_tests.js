/** @odoo-module **/

import { click, editInput, getFixture, triggerEvent } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

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
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                        },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("AttachDocument");

    QUnit.test("attach document widget calls action with attachment ids", async function (assert) {
        serviceRegistry.add("http", {
            start: () => ({
                post: (route, params) => {
                    assert.step("post");
                    assert.strictEqual(route, "/web/binary/upload_attachment");
                    assert.strictEqual(params.model, "partner");
                    assert.strictEqual(params.id, 1);
                    return '[{ "id": 5 }, { "id": 2 }]';
                },
            }),
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "my_action") {
                    assert.step("my_action");
                    assert.deepEqual(args.model, "partner");
                    assert.deepEqual(args.args, [1]);
                    assert.deepEqual(args.kwargs.attachment_ids, [5, 2]);
                    return true;
                }
                if (args.method === "write") {
                    assert.step("write");
                    assert.deepEqual(args.args[1], { display_name: "yop" });
                }
            },
            arch: `
                <form>
                    <widget name="attach_document" action="my_action" string="Attach document"/>
                    <field name="display_name" required="1"/>
                </form>`,
        });

        await editInput(target, "[name='display_name'] input", "yop");
        await click(target, ".o_attach_document");
        await triggerEvent(
            target,
            ".o_file_input input",
            "change",
            {},
            { skipVisibilityCheck: true }
        );
        assert.verifySteps(["write", "post", "my_action"]);
    });
});
