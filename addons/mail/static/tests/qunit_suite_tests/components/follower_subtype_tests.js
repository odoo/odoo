/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("follower_subtype_tests.js");

        QUnit.skipRefactoring("simplest layout of a followed subtype", async function (assert) {
            assert.expect(5);

            const pyEnv = await startServer();
            const subtypeId = pyEnv["mail.message.subtype"].create({
                default: true,
                name: "TestSubtype",
            });
            const followerId = pyEnv["mail.followers"].create({
                display_name: "François Perusse",
                partner_id: pyEnv.currentPartnerId,
                res_model: "res.partner",
                res_id: pyEnv.currentPartnerId,
                subtype_ids: [subtypeId],
            });
            pyEnv["res.partner"].write([pyEnv.currentPartnerId], {
                message_follower_ids: [followerId],
            });
            const { click, openView } = await start({
                // FIXME: should adapt mock server code to provide `hasWriteAccess`
                async mockRPC(route, args, performRPC) {
                    if (route === "/mail/thread/data") {
                        // mimic user with write access
                        const res = await performRPC(...arguments);
                        res["hasWriteAccess"] = true;
                        return res;
                    }
                },
            });
            await openView({
                res_model: "res.partner",
                res_id: pyEnv.currentPartnerId,
                views: [[false, "form"]],
            });
            await click(".o_FollowerListMenuView_buttonFollowers");
            await click(".o_FollowerView_editButton");
            assert.containsOnce(
                document.body,
                ".o_FollowerSubtypeView:contains(TestSubtype)",
                "should have a follower subtype for 'TestSubtype'"
            );
            assert.containsOnce(
                document.querySelector(".o_FollowerSubtypeView"),
                ".o_FollowerSubtypeView_label",
                "should have a label"
            );
            assert.containsOnce(
                $(".o_FollowerSubtypeView:contains(TestSubtype)"),
                ".o_FollowerSubtypeView_checkbox",
                "should have a checkbox"
            );
            assert.strictEqual(
                $(".o_FollowerSubtypeView:contains(TestSubtype) .o_FollowerSubtypeView_label")[0]
                    .textContent,
                "TestSubtype",
                "should have the name of the subtype as label"
            );
            assert.ok(
                $(".o_FollowerSubtypeView:contains(TestSubtype) .o_FollowerSubtypeView_checkbox")[0]
                    .checked,
                "checkbox should be checked as follower subtype is followed"
            );
        });

        QUnit.skipRefactoring("simplest layout of a not followed subtype", async function (assert) {
            assert.expect(1);

            const pyEnv = await startServer();
            pyEnv["mail.message.subtype"].create({
                default: true,
                name: "TestSubtype",
            });
            const followerId = pyEnv["mail.followers"].create({
                display_name: "François Perusse",
                partner_id: pyEnv.currentPartnerId,
                res_model: "res.partner",
                res_id: pyEnv.currentPartnerId,
            });
            pyEnv["res.partner"].write([pyEnv.currentPartnerId], {
                message_follower_ids: [followerId],
            });
            const { click, openView } = await start({
                // FIXME: should adapt mock server code to provide `hasWriteAccess`
                async mockRPC(route, args, performRPC) {
                    if (route === "/mail/thread/data") {
                        // mimic user with write access
                        const res = await performRPC(...arguments);
                        res["hasWriteAccess"] = true;
                        return res;
                    }
                },
            });
            await openView({
                res_model: "res.partner",
                res_id: pyEnv.currentPartnerId,
                views: [[false, "form"]],
            });
            await click(".o_FollowerListMenuView_buttonFollowers");
            await click(".o_FollowerView_editButton");
            assert.notOk(
                $(".o_FollowerSubtypeView:contains(TestSubtype) .o_FollowerSubtypeView_checkbox")[0]
                    .checked,
                "checkbox should not be checked as follower subtype is not followed"
            );
        });

        QUnit.skipRefactoring("toggle follower subtype checkbox", async function (assert) {
            assert.expect(3);

            const pyEnv = await startServer();
            const followerSubtypeId = pyEnv["mail.message.subtype"].create({
                default: true,
                name: "TestSubtype",
            });
            const followerId = pyEnv["mail.followers"].create({
                display_name: "François Perusse",
                partner_id: pyEnv.currentPartnerId,
                res_model: "res.partner",
                res_id: pyEnv.currentPartnerId,
            });
            pyEnv["res.partner"].write([pyEnv.currentPartnerId], {
                message_follower_ids: [followerId],
            });
            const { click, openView } = await start({
                // FIXME: should adapt mock server code to provide `hasWriteAccess`
                async mockRPC(route, args, performRPC) {
                    if (route === "/mail/thread/data") {
                        // mimic user with write access
                        const res = await performRPC(...arguments);
                        res["hasWriteAccess"] = true;
                        return res;
                    }
                },
            });
            await openView({
                res_model: "res.partner",
                res_id: pyEnv.currentPartnerId,
                views: [[false, "form"]],
            });
            await click(".o_FollowerListMenuView_buttonFollowers");
            await click(".o_FollowerView_editButton");
            assert.notOk(
                document.querySelector(
                    `.o_FollowerSubtypeView[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtypeView_checkbox`
                ).checked,
                "checkbox should not be checked as follower subtype is not followed"
            );

            await click(
                `.o_FollowerSubtypeView[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtypeView_checkbox`
            );
            assert.ok(
                document.querySelector(
                    `.o_FollowerSubtypeView[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtypeView_checkbox`
                ).checked,
                "checkbox should now be checked"
            );

            await click(
                `.o_FollowerSubtypeView[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtypeView_checkbox`
            );
            assert.notOk(
                document.querySelector(
                    `.o_FollowerSubtypeView[data-follower-subtype-id="${followerSubtypeId}"] .o_FollowerSubtypeView_checkbox`
                ).checked,
                "checkbox should be no more checked"
            );
        });
    });
});
