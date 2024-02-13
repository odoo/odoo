/** @odoo-module */

import { test } from "@odoo/hoot";
import { click, contains, openFormView, start, startServer } from "../../mail_test_helpers";
import { constants, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { MailThread } from "../../mock_server/mock_models/mail_thread";

test.skip("simplest layout of a followed subtype", async () => {
    const pyEnv = await startServer();
    const subtypeId = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype",
    });
    const followerId = pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: constants.PARTNER_ID,
        res_model: "res.partner",
        res_id: constants.PARTNER_ID,
        subtype_ids: [subtypeId],
    });
    pyEnv["res.partner"].write([constants.PARTNER_ID], { message_follower_ids: [followerId] });
    patchWithCleanup(MailThread.prototype, {
        _get_mail_thread_data() {
            // mimic user with write access
            const res = super._get_mail_thread_data(...arguments);
            res["hasWriteAccess"] = true;
            return res;
        },
    });
    await start();
    await openFormView("res.partner", constants.PARTNER_ID);
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

test.skip("simplest layout of a not followed subtype", async () => {
    const pyEnv = await startServer();
    const subtypeId = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype",
    });
    const followerId = pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: constants.PARTNER_ID,
        res_model: "res.partner",
        res_id: constants.PARTNER_ID,
    });
    pyEnv["res.partner"].write([constants.PARTNER_ID], { message_follower_ids: [followerId] });
    patchWithCleanup(MailThread.prototype, {
        _get_mail_thread_data() {
            // mimic user with write access
            const res = super._get_mail_thread_data(...arguments);
            res["hasWriteAccess"] = true;
            return res;
        },
    });
    await start();
    await openFormView("res.partner", constants.PARTNER_ID);
    await click(".o-mail-Followers-button");
    await click("button[title='Edit subscription']");
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:not(:checked)`
    );
});

test.skip("toggle follower subtype checkbox", async () => {
    const pyEnv = await startServer();
    const subtypeId = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype",
    });
    const followerId = pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: constants.PARTNER_ID,
        res_model: "res.partner",
        res_id: constants.PARTNER_ID,
    });
    pyEnv["res.partner"].write([constants.PARTNER_ID], { message_follower_ids: [followerId] });
    // FIXME: should adapt mock server code to provide "hasWriteAccess"
    patchWithCleanup(MailThread.prototype, {
        _get_mail_thread_data() {
            // mimic user with write access
            const res = super._get_mail_thread_data(...arguments);
            res["hasWriteAccess"] = true;
            return res;
        },
    });
    await start();
    await openFormView("res.partner", constants.PARTNER_ID);
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

test.skip("follower subtype apply", async () => {
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
        partner_id: constants.PARTNER_ID,
        res_model: "res.partner",
        res_id: constants.PARTNER_ID,
        subtype_ids: [subtypeId1],
    });
    pyEnv["res.partner"].write([constants.PARTNER_ID], { message_follower_ids: [followerId] });
    await start();
    await openFormView("res.partner", constants.PARTNER_ID);
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
