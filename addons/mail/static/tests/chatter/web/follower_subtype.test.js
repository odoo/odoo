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
    await click("[title='Edit Notification Preferences']");
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
    await click("[title='Edit Notification Preferences']");
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
    await click("[title='Edit Notification Preferences']");
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
    await click("[title='Edit Notification Preferences']");
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
    await click(".modal-footer button:text('Update')");
    await contains(".o_notification:text('Notification preferences updated.')");
});

test("unselecting all follower subtypes removes the follower", async () => {
    const pyEnv = await startServer();
    const subtypeId = pyEnv["mail.message.subtype"].create({
        default: true,
        name: "TestSubtype",
    });
    pyEnv["mail.followers"].create({
        display_name: "Jace Beleren",
        partner_id: serverState.partnerId,
        res_model: "res.partner",
        res_id: serverState.partnerId,
        subtype_ids: [subtypeId],
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-Followers-counter:text('1')");
    await click(".o-mail-Followers-button");
    await click("[title='Edit Notification Preferences']");
    await click(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']`
    );
    await contains(
        `.o-mail-FollowerSubtypeDialog-subtype[data-follower-subtype-id='${subtypeId}'] input[type='checkbox']:not(:checked)`
    );
    await click(".modal-footer button:text('Update')");
    await contains(".o_notification:text('You are no longer following this record.')");
    await contains(".o-mail-Followers-counter:text('0')");
});

test("internal subtypes are only listed for internal followers", async () => {
    const pyEnv = await startServer();
    const [threadId, customerId, employeeId] = pyEnv["res.partner"].create([
        { name: "Thread" },
        { name: "Customer", partner_share: true },
        { name: "Employee", partner_share: false },
    ]);
    pyEnv["mail.followers"].create([
        {
            partner_id: employeeId,
            res_model: "res.partner",
            res_id: threadId,
        },
        {
            partner_id: customerId,
            res_model: "res.partner",
            res_id: threadId,
        },
    ]);
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Followers-button");
    await click(".o-mail-Follower:has(:text('Employee')) [title='Edit Notification Preferences']");
    await contains(".o-mail-FollowerSubtypeDialog-subtype", { count: 3 });
    await contains(".o-mail-FollowerSubtypeDialog-subtype:eq(0) label:text('Messages')");
    await contains(".o-mail-FollowerSubtypeDialog-subtype:eq(1) label:text('Notes')");
    await contains(".o-mail-FollowerSubtypeDialog-subtype:eq(2) label:text('Activities')");
    await click(".o-mail-FollowerSubtypeDialog button:text('Discard')");
    await click(".o-mail-Followers-button");
    await click(".o-mail-Follower:has(:text('Customer')) [title='Edit Notification Preferences']");
    await contains(".o-mail-FollowerSubtypeDialog-subtype", { count: 1 });
    await contains(".o-mail-FollowerSubtypeDialog-subtype:eq(0) label:text('Messages')");
});

test("'All Notifications' checkbox toggles every subtype and reflects partial selection", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.followers"].create({
        display_name: "François Perusse",
        partner_id: serverState.partnerId,
        res_model: "res.partner",
        res_id: serverState.partnerId,
    });
    const all = ".o-mail-FollowerSubtypeDialog-allSubtypes input[type='checkbox']";
    const subtype = (index) =>
        `.o-mail-FollowerSubtypeDialog-subtype:eq(${index}) input[type='checkbox']`;
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Followers-button");
    await click("[title='Edit Notification Preferences']");
    // internal follower of a res.partner: the 3 default subtypes, none followed
    await contains(".o-mail-FollowerSubtypeDialog-subtype", { count: 3 });
    await contains(".o-mail-FollowerSubtypeDialog-subtype:eq(0) label:text('Messages')");
    await contains(".o-mail-FollowerSubtypeDialog-subtype:eq(1) label:text('Notes')");
    await contains(".o-mail-FollowerSubtypeDialog-subtype:eq(2) label:text('Activities')");
    await contains(`${all}:not(:checked):not(:indeterminate)`);
    // checking it selects every subtype
    await click(all);
    await contains(`${all}:checked:not(:indeterminate)`);
    await contains(".o-mail-FollowerSubtypeDialog-subtype input[type='checkbox']:checked", {
        count: 3,
    });
    // unchecking it unselects every subtype
    await click(all);
    await contains(`${all}:not(:checked):not(:indeterminate)`);
    await contains(".o-mail-FollowerSubtypeDialog-subtype input[type='checkbox']:not(:checked)", {
        count: 3,
    });
    // selecting only some subtypes shows the intermediate state
    await click(subtype(0));
    await contains(`${all}:indeterminate:not(:checked)`);
    await click(subtype(1));
    await contains(`${all}:indeterminate:not(:checked)`);
    // selecting the last one checks it
    await click(subtype(2));
    await contains(`${all}:checked:not(:indeterminate)`);
});
