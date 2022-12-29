/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;
QUnit.module("follower subtype", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("simplest layout of a followed subtype", async function (assert) {
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
    await openView({
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        views: [[false, "form"]],
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    await click(".o-mail-chatter-topbar-follower-list-follower-edit-button");
    assert.containsOnce(target, ".o-mail-follower-subtype-dialog-subtype:contains(TestSubtype)");
    assert.containsOnce(
        document.querySelector(".o-mail-follower-subtype-dialog-subtype"),
        ".o-mail-follower-subtype-dialog-subtype-label"
    );
    assert.containsOnce(
        $(".o-mail-follower-subtype-dialog-subtype:contains(TestSubtype)"),
        ".o-mail-follower-subtype-dialog-subtype-checkbox"
    );
    assert.strictEqual(
        $(
            ".o-mail-follower-subtype-dialog-subtype:contains(TestSubtype) .o-mail-follower-subtype-dialog-subtype-label"
        )[0].textContent,
        "TestSubtype"
    );
    assert.ok(
        $(
            ".o-mail-follower-subtype-dialog-subtype:contains(TestSubtype) .o-mail-follower-subtype-dialog-subtype-checkbox"
        )[0].checked
    );
});

QUnit.test("simplest layout of a not followed subtype", async function (assert) {
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
    await openView({
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        views: [[false, "form"]],
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    await click(".o-mail-chatter-topbar-follower-list-follower-edit-button");
    assert.notOk(
        $(
            ".o-mail-follower-subtype-dialog-subtype:contains(TestSubtype) .o-mail-follower-subtype-dialog-subtype-checkbox"
        )[0].checked,
        "checkbox should not be checked as follower subtype is not followed"
    );
});

QUnit.test("toggle follower subtype checkbox", async function (assert) {
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
    await openView({
        res_model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        views: [[false, "form"]],
    });
    await click(".o-mail-chatter-topbar-follower-list-button");
    await click(".o-mail-chatter-topbar-follower-list-follower-edit-button");
    assert.notOk(
        document.querySelector(
            `.o-mail-follower-subtype-dialog-subtype[data-follower-subtype-id="${followerSubtypeId}"] .o-mail-follower-subtype-dialog-subtype-checkbox`
        ).checked,
        "checkbox should not be checked as follower subtype is not followed"
    );

    await click(
        `.o-mail-follower-subtype-dialog-subtype[data-follower-subtype-id="${followerSubtypeId}"] .o-mail-follower-subtype-dialog-subtype-checkbox`
    );
    assert.ok(
        document.querySelector(
            `.o-mail-follower-subtype-dialog-subtype[data-follower-subtype-id="${followerSubtypeId}"] .o-mail-follower-subtype-dialog-subtype-checkbox`
        ).checked
    );

    await click(
        `.o-mail-follower-subtype-dialog-subtype[data-follower-subtype-id="${followerSubtypeId}"] .o-mail-follower-subtype-dialog-subtype-checkbox`
    );
    assert.notOk(
        document.querySelector(
            `.o-mail-follower-subtype-dialog-subtype[data-follower-subtype-id="${followerSubtypeId}"] .o-mail-follower-subtype-dialog-subtype-checkbox`
        ).checked
    );
});
