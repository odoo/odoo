/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { click, contains, insertText } from "@web/../tests/utils";
import {
    createDocumentsView as originalCreateDocumentsView,
    loadServices,
} from "./documents_test_utils";

async function createDocumentsActivityView(records, onRouteCalled, params) {
    await originalCreateDocumentsView({
        serverData: { models: pyEnv.getData(), views: {} },
        mockRPC: function (route, args) {
            if (args.method === "web_search_read" && args.model === "documents.document") {
                // the domain is [["activity_ids.active", "in", [true, false]]]
                // which is not supported by the server mocking for 2 reasons:
                // - the relational fields have only their ids and not an object with the
                //   values of the records
                // - the domain evaluation does not traverse the m2m / o2m
                //   (see domain.js@matchCondition)
                return { records: records };
            }
            if (onRouteCalled) {
                onRouteCalled(args);
            }
        },
        type: "activity",
        resModel: "documents.document",
        arch: `
        <activity string="Documents" js_class="documents_activity">
            <templates>
                <div t-name="activity-box">
                    <div>
                        <field name="folder_id" invisible="1"/>
                        <field name="name" required="True"/>
                        <field name="owner_id" invisible="1"/>
                        <field name="activity_ids" invisible="1"/>
                    </div>
                </div>
            </templates>
        </activity>
        `,
        ...params,
    });
}

let target;
let records;
let pyEnv;

QUnit.module("documents", {}, function () {
    QUnit.module(
        "documents_activity_tests.js",
        {
            async beforeEach() {
                loadServices();

                pyEnv = await startServer();
                const recordIds = pyEnv["documents.document"].create([
                    {
                        activity_ids: [pyEnv["mail.activity"].create({})],
                        activity_state: "today",
                        name: "Document 1",
                        res_model_name: "Task",
                        res_name: "Task 1",
                    },
                    {
                        attachment_id: pyEnv["ir.attachment"].create({}),
                        mimetype: "application/pdf",
                        name: "Document 2",
                        res_model_name: "Task",
                        res_name: "Task 2",
                    },
                    {
                        activity_ids: [pyEnv["mail.activity"].create({})],
                        attachment_id: pyEnv["ir.attachment"].create({}),
                        mimetype: "application/pdf",
                        name: "Document 3",
                        res_model_name: "Task",
                        res_name: "Task 3",
                    },
                    {
                        activity_ids: [pyEnv["mail.activity"].create({})],
                        attachment_id: pyEnv["ir.attachment"].create({}),
                        mimetype: "application/pdf",
                        name: "Document 4",
                        res_model_name: "Task",
                        res_name: "Task 4",
                        active: false,
                    },
                    {
                        activity_ids: [pyEnv["mail.activity"].create({})],
                        attachment_id: pyEnv["ir.attachment"].create({}),
                        mimetype: "application/pdf",
                        name: "Document 5",
                        res_model_name: "Task",
                        res_name: "Task 5",
                        active: false,
                    },
                ]);
                records = pyEnv["documents.document"].search_read([
                    ["id", "in", recordIds],
                    ["active", "in", [true, false]],
                ]);
                setupViewRegistries();
                target = getFixture();
            },
        },
        function () {
            QUnit.skip("documents activity basic rendering", async function (assert) {
                function onRouteCalled(args) {
                    if (args.method === "action_archive" && args.model === "documents.document") {
                        assert.step("action_archive");
                    }
                }
                await createDocumentsActivityView(
                    [records[0], records[1], records[2]],
                    onRouteCalled
                );

                // Document 2 has no activity, so it's not visible
                const recordsNames = [...target.querySelectorAll(".o_activity_record")].map(
                    (record) => record.innerText
                );
                assert.deepEqual(recordsNames, ["Document 1", "Document 3"]);

                // open the second document
                await click(".o_data_row:nth-child(2) .o_activity_record");
                await nextTick();
                assert.strictEqual(
                    document.querySelector(
                        ".o_documents_inspector .o_field_char[name='name'] input"
                    ).value,
                    "Document 3"
                );

                // open the PDF viewer
                assert.containsNone(target, ".o-FileViewer");
                await click(".o_preview_available");
                await nextTick();
                assert.containsOnce(target, ".o-FileViewer");
                assert.containsOnce(target, ".o-FileViewer .fa-scissors");

                // close the PDF viewer
                await click(".o-FileViewer-main");
                await nextTick();
                assert.containsNone(target, ".o-FileViewer");

                // move the second document to the trash
                await click(".o_documents_inspector .fa-trash");
                await nextTick();
                const confirmDeletionButton = document.querySelector(".modal button:first-child");
                assert.ok(confirmDeletionButton);
                assert.strictEqual(confirmDeletionButton.innerText, "Move to trash");
                assert.verifySteps([]);
                await confirmDeletionButton.click();
                assert.verifySteps(["action_archive"]);
            });

            QUnit.skip("documents activity unlink record", async function (assert) {
                function onRouteCalled(args) {
                    if (args.method === "unlink" && args.model === "documents.document") {
                        assert.step("unlink");
                    }
                }

                await createDocumentsActivityView(
                    [records[0], records[3], records[4]],
                    onRouteCalled,
                    {
                        domain: [["active", "in", [true, false]]],
                    }
                );

                // open the second document
                await click(".o_data_row:nth-child(2) .o_activity_record");
                await nextTick();
                assert.strictEqual(
                    document.querySelector(
                        ".o_documents_inspector .o_field_char[name='name'] input"
                    ).value,
                    "Document 4"
                );

                // unlink the second document
                await click(".o_documents_inspector .fa-trash");
                await nextTick();
                const confirmDeletionButton = document.querySelector(".modal button:first-child");
                assert.ok(confirmDeletionButton);
                assert.strictEqual(confirmDeletionButton.innerText, "Delete permanently");
                assert.verifySteps([]);
                await confirmDeletionButton.click();
                assert.verifySteps(["unlink"]);
            });

            QUnit.skip(
                "document inspector: update document info from activity view",
                async function (assert) {
                    assert.expect(11);
                    function onRouteCalled(args) {
                        if (args.method === "write") {
                            assert.deepEqual(args.args[0], [records[0].id]);
                            assert.deepEqual(args.args[1], { name: "Document 1A" });
                            assert.step("documents.documents/write");
                        }
                    }
                    await createDocumentsActivityView(records, onRouteCalled);
                    await click(".o_activity_record", { text: "Document 1" });
                    await insertText("input", "A", {
                        parent: [".o_inspector_table tr", { text: "Name" }],
                    });
                    await contains(".o_activity_record", { text: "Document 1A" });
                    await insertText("input", "", {
                        parent: [".o_inspector_table tr", { text: "Name" }],
                        replace: true,
                    });
                    await contains(".modal-content", { text: "No valid record to save" });
                    assert.verifySteps(["documents.documents/write"]);
                }
            );
        }
    );
});
