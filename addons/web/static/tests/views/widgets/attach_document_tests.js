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
                assert.step(args.method);
                if (args.method === "my_action") {
                    assert.deepEqual(args.model, "partner");
                    assert.deepEqual(args.args, [1]);
                    assert.deepEqual(args.kwargs.attachment_ids, [5, 2]);
                    return true;
                }
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], { display_name: "yop" });
                }
                if (args.method === "read") {
                    assert.deepEqual(args.args[0], [1]);
                }
            },
            arch: `
                <form>
                    <widget name="attach_document" action="my_action" string="Attach document"/>
                    <field name="display_name" required="1"/>
                </form>`,
        });
        assert.verifySteps(["get_views", "read"]);

        await editInput(target, "[name='display_name'] input", "yop");
        await click(target, ".o_attach_document");
        await triggerEvent(
            target,
            ".o_file_input input",
            "change",
            {},
            { skipVisibilityCheck: true }
        );
        assert.verifySteps(["write", "read", "post", "my_action", "read"]);
    });

    QUnit.test(
        "attach document widget calls action with attachment ids on a new record",
        async function (assert) {
            serviceRegistry.add("http", {
                start: () => ({
                    post: (route, params) => {
                        assert.step("post");
                        assert.strictEqual(route, "/web/binary/upload_attachment");
                        assert.strictEqual(params.model, "partner");
                        assert.strictEqual(params.id, 2);
                        return '[{ "id": 5 }, { "id": 2 }]';
                    },
                }),
            });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "my_action") {
                        assert.deepEqual(args.model, "partner");
                        assert.deepEqual(args.args, [2]);
                        assert.deepEqual(args.kwargs.attachment_ids, [5, 2]);
                        return true;
                    }
                    if (args.method === "create") {
                        assert.deepEqual(args.args[0], { display_name: "yop" });
                    }
                    if (args.method === "read") {
                        assert.deepEqual(args.args[0], [2]);
                    }
                },
                arch: `
                <form>
                    <widget name="attach_document" action="my_action" string="Attach document"/>
                    <field name="display_name" required="1"/>
                </form>`,
            });
            assert.verifySteps(["get_views", "onchange"]);

            await editInput(target, "[name='display_name'] input", "yop");
            await click(target, ".o_attach_document");
            await triggerEvent(
                target,
                ".o_file_input input",
                "change",
                {},
                { skipVisibilityCheck: true }
            );
            assert.verifySteps(["create", "read", "post", "my_action", "read"]);
        }
    );
});
