import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("simplest layout of a followed subtype", async () => {
    const pyEnv = await startServer();
    const subtypeId = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype",
    });
    pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: serverState.partnerId,
        res_model: "res.partner",
        res_id: serverState.partnerId,
        subtype_ids: [subtypeId],
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Followers-button");
    await click("[title='Edit subscription']");
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] label:text('TestSubtype')`
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:checked`
    );
});

test("simplest layout of a not followed subtype", async () => {
    const pyEnv = await startServer();
    const subtypeId = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype",
    });
    pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: serverState.partnerId,
        res_model: "res.partner",
        res_id: serverState.partnerId,
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Followers-button");
    await click("[title='Edit subscription']");
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:not(:checked)`
    );
});

test("toggle follower subtype checkbox", async () => {
    const pyEnv = await startServer();
    const subtypeId = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype",
    });
    pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: serverState.partnerId,
        res_model: "res.partner",
        res_id: serverState.partnerId,
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Followers-button");
    await click("[title='Edit subscription']");
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

test("follower subtype apply", async () => {
    const pyEnv = await startServer();
    const subtypeId1 = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype1",
    });
    const subtypeId2 = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype2",
    });
    pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: serverState.partnerId,
        res_model: "res.partner",
        res_id: serverState.partnerId,
        subtype_ids: [subtypeId1],
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Followers-button");
    await click("[title='Edit subscription']");
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
    await click(".modal-footer button:text('Apply')");
    await contains(
        ".o_notification:text('The subscription preferences were successfully applied.')"
    );
});

test("external follower only sees non-internal subtypes", async () => {
    const pyEnv = await startServer();
    const subtypeInternal = pyEnv["mail.message.subtype"].search([
        ["internal", "=", true]
    ])[0];
    const subtypeExternal = pyEnv["mail.message.subtype"].search([
        ["internal", "=", false]  
    ])[0];
    const externalPartner = pyEnv["res.partner"].create({
        name: "Guest User",
        email: "guest@example.com",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "guest@example.com",
        partner_ids: [externalPartner],
    });
    pyEnv["mail.followers"].create({
        display_name: "Guest User",
        partner_id: externalPartner,
        res_model: "res.fake",
        res_id: fakeId,
        subtype_ids: [subtypeExternal],
    });
    await start();
    await openFormView("res.fake", fakeId);
    await click(".o-mail-Followers-button");
    await click("[title='Edit subscription']");
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeInternal}']`,
        { count: 0 }
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeExternal}'] label`,
    );
});
