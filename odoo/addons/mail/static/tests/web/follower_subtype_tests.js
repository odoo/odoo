/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("follower subtype");

QUnit.test("simplest layout of a followed subtype", async () => {
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
    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { message_follower_ids: [followerId] });
    const { openView } = await start({
        // FIXME: should adapt mock server code to provide "hasWriteAccess"
        async mockRPC(route, args, performRPC) {
            if (route === "/mail/thread/data") {
                // mimic user with write access
                const res = await performRPC(...arguments);
                res["hasWriteAccess"] = true;
                return res;
            }
        },
    });
    openView({
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        views: [[false, "form"]],
    });
    await click(".o-mail-Followers-button");
    await click("button[title='Edit subscription']");
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] label`,
        { text: "TestSubtype" }
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:checked`
    );
});

QUnit.test("simplest layout of a not followed subtype", async () => {
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
    });
    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { message_follower_ids: [followerId] });
    const { openView } = await start({
        // FIXME: should adapt mock server code to provide "hasWriteAccess"
        async mockRPC(route, args, performRPC) {
            if (route === "/mail/thread/data") {
                // mimic user with write access
                const res = await performRPC(...arguments);
                res["hasWriteAccess"] = true;
                return res;
            }
        },
    });
    openView({
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        views: [[false, "form"]],
    });
    await click(".o-mail-Followers-button");
    await click("button[title='Edit subscription']");
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:not(:checked)`
    );
});

QUnit.test("toggle follower subtype checkbox", async () => {
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
    });
    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { message_follower_ids: [followerId] });
    const { openView } = await start({
        // FIXME: should adapt mock server code to provide "hasWriteAccess"
        async mockRPC(route, args, performRPC) {
            if (route === "/mail/thread/data") {
                // mimic user with write access
                const res = await performRPC(...arguments);
                res["hasWriteAccess"] = true;
                return res;
            }
        },
    });
    openView({
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        views: [[false, "form"]],
    });
    await click(".o-mail-Followers-button");
    await click("button[title='Edit subscription']");
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:not(:checked)`
    );
    await click(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']`
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:checked`
    );
    await click(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']`
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:not(:checked)`
    );
});

QUnit.test("follower subtype apply", async () => {
    const pyEnv = await startServer();
    const subtypeId1 = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype1",
    });
    const subtypeId2 = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype2",
    });
    const followerId = pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        subtype_ids: [subtypeId1],
    });
    pyEnv["res.partner"].write([pyEnv.currentPartnerId], { message_follower_ids: [followerId] });
    const { openView } = await start();
    openView({
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        views: [[false, "form"]],
    });
    await click(".o-mail-Followers-button");
    await click("button[title='Edit subscription']");

    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId1}'] input[type='checkbox']:checked`
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId2}'] input[type='checkbox']:not(:checked)`
    );
    await click(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId1}'] input[type='checkbox']`
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId1}'] input[type='checkbox']:not(:checked)`
    );
    await click(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId2}'] input[type='checkbox']`
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId2}'] input[type='checkbox']:checked`
    );
    await click(".modal-footer button", { text: "Apply" });
    await contains(".o_notification", {
        text: "The subscription preferences were successfully applied.",
    });
});
