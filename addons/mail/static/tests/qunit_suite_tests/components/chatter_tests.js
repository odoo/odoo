/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("chatter", {}, function () {
            QUnit.module("chatter_tests.js");

            QUnit.test(
                "should not display subject when subject is the same as the default subject",
                async function (assert) {
                    assert.expect(1);

                    const pyEnv = await startServer();
                    const fakeRecordId = pyEnv["res.fake"].create({
                        name: "Salutations, voyageur",
                    });
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "res.fake",
                        res_id: fakeRecordId,
                        subject: "Custom Default Subject", // default subject for res.fake, set on the model
                    });
                    const { openView } = await start();
                    await openView({
                        res_id: fakeRecordId,
                        res_model: "res.fake",
                        views: [[false, "form"]],
                    });

                    assert.containsNone(
                        document.body,
                        ".o_MessageView_subject",
                        "should not display subject of the message"
                    );
                }
            );

            QUnit.test(
                "should not display subject when subject is the same as the thread name with custom default subject",
                async function (assert) {
                    assert.expect(1);

                    const pyEnv = await startServer();
                    const fakeRecordId = pyEnv["res.fake"].create({
                        name: "Salutations, voyageur",
                    });
                    pyEnv["mail.message"].create({
                        body: "not empty",
                        model: "res.fake",
                        res_id: fakeRecordId,
                        subject: "Salutations, voyageur",
                    });
                    const { openView } = await start();
                    await openView({
                        res_id: fakeRecordId,
                        res_model: "res.fake",
                        views: [[false, "form"]],
                    });

                    assert.containsNone(
                        document.body,
                        ".o_MessageView_subject",
                        "should not display subject of the message"
                    );
                }
            );
        });
    });
});
