/** @odoo-module **/

import {
    afterNextRender,
    click,
    start,
    startServer,
    nextAnimationFrame,
} from "@mail/../tests/helpers/test_utils";
import { makeDeferred } from "@web/../tests/helpers/utils";

QUnit.module("chatter topbar");

QUnit.test("base rendering", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });

    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsOnce($, "button:contains(Send message)");
    assert.containsOnce($, "button:contains(Log note)");
    assert.containsOnce($, "button:contains(Activities)");
    assert.containsOnce($, "button[aria-label='Attach files']");
    assert.containsOnce($, ".o-Followers");
});

QUnit.test("rendering with multiple partner followers", async (assert) => {
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

    assert.containsOnce($, ".o-Followers");
    assert.containsOnce($, ".o-Followers-button");

    await click(".o-Followers-button");
    assert.containsOnce($, ".o-Followers-dropdown");
    assert.containsN($, ".o-Follower", 2);
    assert.strictEqual($(".o-Follower:eq(0)").text().trim(), "Jean Michang");
    assert.strictEqual($(".o-Follower:eq(1)").text().trim(), "Eden Hazard");
});

QUnit.test("log note toggling", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, "button:contains(Log note)");
    assert.doesNotHaveClass($("button:contains(Log note)"), "o-active");
    assert.containsNone($, ".o-Composer");

    await click("button:contains(Log note)");
    assert.hasClass($("button:contains(Log note)"), "o-active");
    assert.containsOnce($, ".o-Composer .o-Composer-input[placeholder='Log an internal note...']");

    await click("button:contains(Log note)");
    assert.doesNotHaveClass($("button:contains(Log note)"), "o-active");
    assert.containsNone($, ".o-Composer");
});

QUnit.test("send message toggling", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, "button:contains(Send message)");
    assert.doesNotHaveClass($("button:contains(Send message)"), "o-active");
    assert.containsNone($, ".o-Composer");

    await click("button:contains(Send message)");
    assert.hasClass($("button:contains(Send message)"), "o-active");
    assert.containsOnce($, ".o-Composer-input[placeholder='Send a message to followers...']");

    await click("button:contains(Send message)");
    assert.doesNotHaveClass($("button:contains(Send message)"), "o-active");
    assert.containsNone($, ".o-Composer");
});

QUnit.test("log note/send message switching", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, "button:contains(Send message)");
    assert.doesNotHaveClass($("button:contains(Send message)"), "o-active");
    assert.containsOnce($, "button:contains(Log note)");
    assert.doesNotHaveClass($("button:contains(Log note)"), "o-active");
    assert.containsNone($, ".o-Composer");

    await click("button:contains(Send message)");
    assert.hasClass($("button:contains(Send message)"), "o-active");
    assert.doesNotHaveClass($("button:contains(Log note)"), "o-active");
    assert.containsOnce($, ".o-Composer-input[placeholder='Send a message to followers...']");

    await click("button:contains(Log note)");
    assert.doesNotHaveClass($("button:contains(Send message)"), "o-active");
    assert.hasClass($("button:contains(Log note)"), "o-active");
    assert.containsOnce($, ".o-Composer-input[placeholder='Log an internal note...']");
});

QUnit.test("attachment counter without attachments", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, "button[aria-label='Attach files']");
    assert.containsNone($, "button[aria-label='Attach files']:contains(0)");
});

QUnit.test("attachment counter with attachments", async (assert) => {
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
    assert.containsOnce($, "button[aria-label='Attach files']:contains(2)");
});

QUnit.test("attachment counter while loading attachments", async (assert) => {
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
    assert.containsOnce($, "button[aria-label='Attach files'] .fa-spin");
    assert.containsNone($, "button[aria-label='Attach files']:contains(0)");
});

QUnit.test("attachment counter transition when attachments become loaded", async (assert) => {
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
    assert.containsOnce($, "button[aria-label='Attach files'] .fa-spin");

    await afterNextRender(() => deferred.resolve());
    assert.containsNone($, "button[aria-label='Attach files'] .fa-spin");
});

QUnit.test(
    "attachment icon open directly the file uploader if there is no attachment yet",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const { openView } = await start();
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        assert.containsOnce($, ".o-Chatter-fileUploader");
        assert.containsNone($, ".o-AttachmentBox");
    }
);

QUnit.test(
    "attachment icon open the attachment box when there is at least 1 attachment",
    async (assert) => {
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
        assert.containsNone($, ".o-Chatter-fileUploader");
        await click("button[aria-label='Attach files']");
        assert.containsOnce($, ".o-AttachmentBox");
    }
);

QUnit.test("composer state conserved when clicking on another topbar button", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsOnce($, "button:contains(Send message)");
    assert.containsOnce($, "button:contains(Log note)");
    assert.containsOnce($, "button[aria-label='Attach files']");

    await click("button:contains(Log note)");
    assert.containsOnce($, "button:contains(Log note).o-active");
    assert.containsNone($, "button:contains(Send message).o-active");

    $(`button[aria-label='Attach files']`)[0].click();
    await nextAnimationFrame();
    assert.containsOnce($, "button:contains(Log note).o-active");
    assert.containsNone($, "button:contains(Send message).o-active");
});
