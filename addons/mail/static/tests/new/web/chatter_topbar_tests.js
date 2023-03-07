/** @odoo-module **/

import {
    afterNextRender,
    click,
    start,
    startServer,
    nextAnimationFrame,
} from "@mail/../tests/helpers/test_utils";
import { getFixture, makeDeferred } from "@web/../tests/helpers/utils";

let target;
QUnit.module("chatter topbar", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("base rendering", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });

    assert.containsOnce(target, ".o-mail-chatter-topbar");
    assert.containsOnce(target, "button:contains(Send message)");
    assert.containsOnce(target, "button:contains(Log note)");
    assert.containsOnce(target, "button:contains(Activities)");
    assert.containsOnce(target, "button[aria-label='Attach files']");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list");
});

QUnit.test("rendering with multiple partner followers", async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { name: "Eden Hazard" },
        { name: "Jean Michang" },
        { message_follower_ids: [1, 2] },
    ]);
    pyEnv["mail.followers"].create([
        {
            partner_id: partnerId_2,
            res_id: partnerId_3,
            res_model: "res.partner",
        },
        {
            partner_id: partnerId_1,
            res_id: partnerId_3,
            res_model: "res.partner",
        },
    ]);
    const { openView } = await start();
    await openView({
        res_id: partnerId_3,
        res_model: "res.partner",
        views: [[false, "form"]],
    });

    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-button");

    await click(".o-mail-chatter-topbar-follower-list-button");
    assert.containsOnce(target, ".o-mail-chatter-topbar-follower-list-dropdown");
    assert.containsN(target, ".o-mail-chatter-topbar-follower-list-follower", 2);
    assert.strictEqual(
        target
            .querySelectorAll(".o-mail-chatter-topbar-follower-list-follower")[0]
            .textContent.trim(),
        "Jean Michang"
    );
    assert.strictEqual(
        target
            .querySelectorAll(".o-mail-chatter-topbar-follower-list-follower")[1]
            .textContent.trim(),
        "Eden Hazard"
    );
});

QUnit.test("log note toggling", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button:contains(Log note)");
    assert.doesNotHaveClass($(target).find("button:contains(Log note)"), "o-active");
    assert.containsNone(target, ".o-mail-composer");

    await click("button:contains(Log note)");
    assert.hasClass($(target).find("button:contains(Log note)"), "o-active");
    assert.containsOnce(
        target,
        ".o-mail-composer .o-mail-composer-textarea[placeholder='Log an internal note...']"
    );

    await click("button:contains(Log note)");
    assert.doesNotHaveClass($(target).find("button:contains(Log note)"), "o-active");
    assert.containsNone(target, ".o-mail-composer");
});

QUnit.test("send message toggling", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button:contains(Send message)");
    assert.doesNotHaveClass($(target).find("button:contains(Send message)"), "o-active");
    assert.containsNone(target, ".o-mail-composer");

    await click("button:contains(Send message)");
    assert.hasClass($(target).find("button:contains(Send message)"), "o-active");
    assert.containsOnce(
        target,
        ".o-mail-composer-textarea[placeholder='Send a message to followers...']"
    );

    await click("button:contains(Send message)");
    assert.doesNotHaveClass($(target).find("button:contains(Send message)"), "o-active");
    assert.containsNone(target, ".o-mail-composer");
});

QUnit.test("log note/send message switching", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button:contains(Send message)");
    assert.doesNotHaveClass($(target).find("button:contains(Send message)"), "o-active");
    assert.containsOnce(target, "button:contains(Log note)");
    assert.doesNotHaveClass($(target).find("button:contains(Log note)"), "o-active");
    assert.containsNone(target, ".o-mail-composer");

    await click("button:contains(Send message)");
    assert.hasClass($(target).find("button:contains(Send message)"), "o-active");
    assert.doesNotHaveClass($(target).find("button:contains(Log note)"), "o-active");
    assert.containsOnce(
        target,
        ".o-mail-composer-textarea[placeholder='Send a message to followers...']"
    );

    await click("button:contains(Log note)");
    assert.doesNotHaveClass($(target).find("button:contains(Send message)"), "o-active");
    assert.hasClass($(target).find("button:contains(Log note)"), "o-active");
    assert.containsOnce(target, ".o-mail-composer-textarea[placeholder='Log an internal note...']");
});

QUnit.test("attachment counter without attachments", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button[aria-label='Attach files']");
    assert.containsNone(target, "button[aria-label='Attach files']:contains(0)");
});

QUnit.test("attachment counter with attachments", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
        {
            mimetype: "text/plain",
            name: "Blu.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
    ]);
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button[aria-label='Attach files']:contains(2)");
});

QUnit.test("attachment counter while loading attachments", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start({
        async mockRPC(route) {
            if (route.includes("/mail/thread/data")) {
                await makeDeferred(); // simulate long loading
            }
        },
    });
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button[aria-label='Attach files'] .fa-spin");
    assert.containsNone(target, "button[aria-label='Attach files']:contains(0)");
});

QUnit.test("attachment counter transition when attachments become loaded", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const deferred = makeDeferred();
    const { openView } = await start({
        async mockRPC(route) {
            if (route.includes("/mail/thread/data")) {
                await deferred;
            }
        },
    });
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button[aria-label='Attach files'] .fa-spin");

    await afterNextRender(() => deferred.resolve());
    assert.containsNone(target, "button[aria-label='Attach files'] .fa-spin");
});

QUnit.test(
    "attachment icon open directly the file uploader if there is no attachment yet",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const { openView } = await start();
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        assert.containsOnce(target, ".o-mail-chatter-file-uploader");
        assert.containsNone(target, ".o-mail-attachment-box");
    }
);

QUnit.test(
    "attachment icon open the attachment box when there is at least 1 attachment",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        pyEnv["ir.attachment"].create([
            {
                mimetype: "text/plain",
                name: "Blah.txt",
                res_id: partnerId,
                res_model: "res.partner",
            },
        ]);
        const { openView } = await start();
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        assert.containsNone(target, ".o-mail-chatter-file-uploader");
        await click("button[aria-label='Attach files']");
        assert.containsOnce(target, ".o-mail-attachment-box");
    }
);

QUnit.test(
    "composer state conserved when clicking on another topbar button",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const { openFormView } = await start();
        await openFormView("res.partner", partnerId);
        assert.containsOnce(target, ".o-mail-chatter-topbar");
        assert.containsOnce(target, "button:contains(Send message)");
        assert.containsOnce(target, "button:contains(Log note)");
        assert.containsOnce(target, "button[aria-label='Attach files']");

        await click("button:contains(Log note)");
        assert.containsOnce(target, "button:contains(Log note).o-active");
        assert.containsNone(target, "button:contains(Send message).o-active");

        $(`button[aria-label='Attach files']`)[0].click();
        await nextAnimationFrame();
        assert.containsOnce(target, "button:contains(Log note).o-active");
        assert.containsNone(target, "button:contains(Send message).o-active");
    }
);
