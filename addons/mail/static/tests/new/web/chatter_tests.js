/** @odoo-module **/

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    click,
    dragenterFiles,
    dropFiles,
    insertText,
    isScrolledTo,
    start,
    startServer,
    waitFormViewLoaded,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";

import { editInput, triggerHotkey } from "@web/../tests/helpers/utils";
import { file } from "web.test_utils";

const { createFile } = file;

QUnit.module("chatter");

QUnit.test("simple chatter on a record", async (assert) => {
    const { openFormView, pyEnv } = await start({
        mockRPC(route, args) {
            if (route.startsWith("/mail")) {
                assert.step(route);
            }
        },
    });
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsOnce($, ".o-Thread");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/thread/data",
        "/mail/thread/messages",
    ]);
});

QUnit.test("displayname is used when sending a message", async (assert) => {
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    assert.containsOnce($, '.o-Chatter:contains(To followers of:  "John Doe")');
});

QUnit.test("can post a message on a record thread", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const { openFormView } = await start({
        mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step(route);
                const expected = {
                    post_data: {
                        body: "hey",
                        attachment_ids: [],
                        message_type: "comment",
                        partner_ids: [],
                        subtype_xmlid: "mail.mt_comment",
                    },
                    thread_id: partnerId,
                    thread_model: "res.partner",
                };
                assert.deepEqual(args, expected);
            }
        },
    });
    await openFormView("res.partner", partnerId);
    assert.containsNone($, ".o-Composer");

    await click("button:contains(Send message)");
    assert.containsOnce($, ".o-Composer");

    await editInput(document.body, ".o-Composer-input", "hey");
    assert.containsNone($, ".o-Message");

    await click(".o-Composer button:contains(Send)");
    assert.containsOnce($, ".o-Message");
    assert.verifySteps(["/mail/message/post"]);
});

QUnit.test("can post a note on a record thread", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const { openFormView } = await start({
        mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step(route);
                const expected = {
                    post_data: {
                        attachment_ids: [],
                        body: "hey",
                        message_type: "comment",
                        partner_ids: [],
                        subtype_xmlid: "mail.mt_note",
                    },
                    thread_id: partnerId,
                    thread_model: "res.partner",
                };
                assert.deepEqual(args, expected);
            }
        },
    });
    await openFormView("res.partner", partnerId);
    assert.containsNone($, ".o-Composer");

    await click("button:contains(Log note)");
    assert.containsOnce($, ".o-Composer");

    await editInput(document.body, ".o-Composer-input", "hey");
    assert.containsNone($, ".o-Message");

    await click(".o-Composer button:contains(Send)");
    assert.containsOnce($, ".o-Message");
    assert.verifySteps(["/mail/message/post"]);
});

QUnit.test("No attachment loading spinner when creating records", async (assert) => {
    const { openFormView } = await start();
    await openFormView("res.partner");
    assert.containsOnce($, "button[aria-label='Attach files']");
    assert.containsNone($, "button[aria-label='Attach files'] .fa-spin");
});

QUnit.test(
    "No attachment loading spinner when switching from loading record to creation of record",
    async (assert) => {
        const { openFormView, pyEnv } = await start({
            async mockRPC(route) {
                if (route === "/mail/thread/data") {
                    await new Promise(() => {});
                }
            },
        });
        const partnerId = pyEnv["res.partner"].create({ name: "John" });
        await openFormView("res.partner", partnerId, { waitUntilDataLoaded: false });
        assert.containsOnce($, "button[aria-label='Attach files'] .fa-spin");
        await click(".o_form_button_create");
        assert.containsNone($, "button[aria-label='Attach files'] .fa-spin");
    }
);

QUnit.test("Composer toggle state is kept when switching from aside to bottom", async (assert) => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    patchUiSize({ size: SIZES.LG });
    await waitFormViewLoaded(() => window.dispatchEvent(new Event("resize")), {
        resId: partnerId,
        resModel: "res.partner",
    });
    assert.containsOnce($, ".o-Composer-input");
});

QUnit.test("Textarea content is kept when switching from aside to bottom", async (assert) => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await editInput(document.body, ".o-Composer-input", "Hello world !");
    patchUiSize({ size: SIZES.LG });
    await waitFormViewLoaded(() => window.dispatchEvent(new Event("resize")), {
        resId: partnerId,
        resModel: "res.partner",
    });
    assert.strictEqual($(".o-Composer-input").val(), "Hello world !");
});

QUnit.test("Composer type is kept when switching from aside to bottom", async (assert) => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button:contains(Log note)");
    patchUiSize({ size: SIZES.LG });
    await waitFormViewLoaded(() => window.dispatchEvent(new Event("resize")), {
        resId: partnerId,
        resModel: "res.partner",
    });
    assert.hasClass(
        $("button:contains(Log note)"),
        "btn-odoo",
        "Active button should be the log note button"
    );
    assert.doesNotHaveClass($("button:contains(Send message)"), "btn-odoo");
});

QUnit.test("chatter: drop attachments", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    let files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
        await createFile({
            content: "hello, worlduh",
            contentType: "text/plain",
            name: "text2.txt",
        }),
    ];
    await afterNextRender(() => dragenterFiles($(".o-Chatter")[0]));
    assert.containsOnce($, ".o-Dropzone");
    assert.containsNone($, ".o-AttachmentCard");

    await afterNextRender(() => dropFiles($(".o-Dropzone")[0], files));
    assert.containsN($, ".o-AttachmentCard", 2);

    await afterNextRender(() => dragenterFiles($(".o-Chatter")[0]));
    files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
    ];
    await afterNextRender(() => dropFiles($(".o-Dropzone")[0], files));
    assert.containsN($, ".o-AttachmentCard", 3);
});

QUnit.test("should display subject when subject isn't infered from the record", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
        subject: "Salutations, voyageur",
    });
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-Message:contains(Subject: Salutations, voyageur)");
});

QUnit.test("should not display user notification messages in chatter", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        message_type: "user_notification",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsNone($, ".o-Message");
});

QUnit.test('post message with "CTRL-Enter" keyboard shortcut in chatter', async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsNone($, ".o-Message");

    await click("button:contains(Send message)");
    await insertText(".o-Composer-input", "Test");
    await afterNextRender(() => triggerHotkey("control+Enter"));
    assert.containsOnce($, ".o-Message");
});

QUnit.test("base rendering when chatter has no attachment", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-Chatter");
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsNone($, ".o-AttachmentBox");
    assert.containsOnce($, ".o-Thread");
    assert.containsN($, ".o-Message", 30);
});

QUnit.test("base rendering when chatter has no record", async (assert) => {
    const { openView } = await start();
    await openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-Chatter");
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsNone($, ".o-AttachmentBox");
    assert.containsOnce($, ".o-Chatter .o-Thread");
    assert.containsOnce($, ".o-Message");
    assert.strictEqual($(".o-Message-body").text(), "Creating a new record...");
    assert.containsNone($, "button:contains(Load More)");
    assert.containsOnce($, ".o-Message-actions");
    assert.containsNone($, ".o-Message-actions i");
});

QUnit.test("base rendering when chatter has attachments", async (assert) => {
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
    assert.containsOnce($, ".o-Chatter");
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsNone($, ".o-AttachmentBox");
});

QUnit.test("show attachment box", async (assert) => {
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
    assert.containsOnce($, ".o-Chatter");
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsOnce($, "button[aria-label='Attach files']");
    assert.containsOnce($, "button[aria-label='Attach files']:contains(2)");
    assert.containsNone($, ".o-AttachmentBox");

    await click("button[aria-label='Attach files']");
    assert.containsOnce($, ".o-AttachmentBox");
});

QUnit.test("composer show/hide on log note/send message [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce($, "button:contains(Send message)");
    assert.containsOnce($, "button:contains(Log note)");
    assert.containsNone($, ".o-Composer");

    await click("button:contains(Send message)");
    assert.containsOnce($, ".o-Composer");
    assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);

    await click("button:contains(Log note)");
    assert.containsOnce($, ".o-Composer");
    assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);

    await click("button:contains(Log note)");
    assert.containsNone($, ".o-Composer");

    await click("button:contains(Send message)");
    assert.containsOnce($, ".o-Composer");

    await click("button:contains(Send message)");
    assert.containsNone($, ".o-Composer");
});

QUnit.test('do not post message with "Enter" keyboard shortcut', async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsNone($, ".o-Message");

    await click("button:contains(Send message)");
    await insertText(".o-Composer-input", "Test");
    await triggerHotkey("Enter");
    assert.containsNone($, ".o-Message");
});

QUnit.test(
    "should not display subject when subject is the same as the thread name",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            name: "Salutations, voyageur",
        });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: partnerId,
            subject: "Salutations, voyageur",
        });
        const { openView } = await start();
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        assert.containsNone($, ".o-Message:contains(Salutations, voyageur)");
    }
);

QUnit.test("scroll position is kept when navigating from one record to another", async (assert) => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Harry Potter" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Ron Weasley" });
    // Fill both channels with random messages in order for the scrollbar to
    // appear.
    pyEnv["mail.message"].create(
        Array(40)
            .fill(0)
            .map((_, index) => ({
                body: "Non Empty Body ".repeat(25),
                model: "res.partner",
                res_id: index & 1 ? partnerId_1 : partnerId_2,
            }))
    );
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId_1);
    const scrolltop_1 = $(".o-Chatter-scrollable")[0].scrollHeight / 2;
    $(".o-Chatter-scrollable")[0].scrollTo({ top: scrolltop_1 });
    await openFormView("res.partner", partnerId_2);
    const scrolltop_2 = $(".o-Chatter-scrollable")[0].scrollHeight / 3;
    $(".o-Chatter-scrollable")[0].scrollTo({ top: scrolltop_2 });
    await openFormView("res.partner", partnerId_1);
    assert.ok(isScrolledTo($(".o-Chatter-scrollable")[0], scrolltop_1));

    await openFormView("res.partner", partnerId_2);
    assert.ok(isScrolledTo($(".o-Chatter-scrollable")[0], scrolltop_2));
});

QUnit.test("basic chatter rendering", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "second partner" });
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-Chatter");
});

QUnit.test("basic chatter rendering without activities", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "second partner" });
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-Chatter");
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsOnce($, "button[aria-label='Attach files']");
    assert.containsNone($, "button:contains(Activities)");
    assert.containsOnce($, ".o-Followers");
    assert.containsOnce($, ".o-Thread");
});

QUnit.test(
    'chatter just contains "creating a new record" message during the creation of a new record after having displayed a chatter for an existing record',
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const views = {
            "res.partner,false,form": `
                <form string="Partners">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                    <div class="oe_chatter">
                        <field name="message_ids"/>
                    </div>
                </form>`,
        };
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
        await click(".o_form_button_create");
        assert.containsOnce($, ".o-Message");
        assert.containsOnce($, ".o-Message-body:contains(Creating a new record...)");
    }
);

QUnit.test(
    "should not display subject when subject is the same as the default subject",
    async (assert) => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.fake",
            res_id: fakeId,
            subject: "Custom Default Subject", // default subject for res.fake, set on the model
        });
        const { openFormView } = await start();
        await openFormView("res.fake", fakeId);
        assert.containsNone($, ".o-Message:contains(Custom Default Subject)");
    }
);

QUnit.test(
    "should not display subject when subject is the same as the thread name with custom default subject",
    async (assert) => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.fake",
            res_id: fakeId,
            subject: "Salutations, voyageur",
        });
        const { openFormView } = await start();
        await openFormView("res.fake", fakeId);
        assert.containsNone($, ".o-Message:contains(Custom Default Subject)");
    }
);

QUnit.test("basic chatter rendering without followers", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "second partner" });
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-Chatter");
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsOnce($, "button[aria-label='Attach files']");
    assert.containsOnce($, "button:contains(Activities)");
    assert.containsNone(
        $,
        ".o-Followers",
        "there should be no followers menu because the 'message_follower_ids' field is not present in 'oe_chatter'"
    );
    assert.containsOnce($, ".o-Chatter .o-Thread");
});

QUnit.test("basic chatter rendering without messages", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "second partner" });
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    assert.containsOnce($, ".o-Chatter");
    assert.containsOnce($, ".o-Chatter-topbar");
    assert.containsOnce($, "button[aria-label='Attach files']");
    assert.containsOnce($, "button:contains(Activities)");
    assert.containsOnce($, ".o-Followers");
    assert.containsNone(
        $,
        ".o-Chatter .o-Thread",
        "there should be no thread because the 'message_ids' field is not present in 'oe_chatter'"
    );
});

QUnit.test("chatter updating", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { display_name: "first partner" },
        { display_name: "second partner" },
    ]);
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId_2,
    });
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openFormView } = await start({ serverData: { views } });
    await openFormView("res.partner", partnerId_1, {
        props: { resIds: [partnerId_1, partnerId_2] },
    });
    await click(".o_pager_next");
    assert.containsOnce($, ".o-Message");
});

QUnit.test("post message on draft record", async (assert) => {
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click("button:contains(Send message)");
    await editInput(document.body, ".o-Composer-input", "Test");
    await click(".o-Composer button:contains(Send)");
    assert.containsOnce($, ".o-Message");
    assert.containsOnce($, ".o-Message:contains(Test)");
});

QUnit.test(
    "schedule activities on draft record should prompt with scheduling an activity (proceed with action)",
    async (assert) => {
        const views = {
            "res.partner,false,form": `
                <form string="Partners">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                    <div class="oe_chatter">
                        <field name="activity_ids"/>
                    </div>
                </form>`,
        };
        const { openView } = await start({ serverData: { views } });
        await openView({ res_model: "res.partner", views: [[false, "form"]] });
        await click("button:contains(Activities)");
        assert.containsOnce($, ".o_dialog:contains(Schedule Activity)");
    }
);

QUnit.test("upload attachment on draft record", async (assert) => {
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    assert.containsNone($, ".button[aria-label='Attach files']:contains(1)");
    await afterNextRender(() => dragenterFiles($(".o-Chatter")[0]));
    await afterNextRender(() => dropFiles($(".o-Dropzone")[0], [file]));
    await waitUntil("button[aria-label='Attach files']:contains(1)");
});
