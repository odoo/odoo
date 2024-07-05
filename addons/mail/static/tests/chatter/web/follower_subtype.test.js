import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { MailThread } from "../../mock_server/mock_models/mail_thread";

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
    patchWithCleanup(MailThread.prototype, {
        _thread_to_store(ids, store) {
            // mimic user with write access
            super._thread_to_store(...arguments);
            store.add("Thread", { hasWriteAccess: true, id: ids[0], model: this._name });
        },
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
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
    patchWithCleanup(MailThread.prototype, {
        _thread_to_store(ids, store) {
            // mimic user with write access
            super._thread_to_store(...arguments);
            store.add("Thread", { hasWriteAccess: true, id: ids[0], model: this._name });
        },
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Followers-button");
    await click("button[title='Edit subscription']");
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
    patchWithCleanup(MailThread.prototype, {
        _thread_to_store(ids, store) {
            // mimic user with write access
            super._thread_to_store(...arguments);
            store.add("Thread", { hasWriteAccess: true, id: ids[0], model: this._name });
        },
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
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
