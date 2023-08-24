/* @odoo-module */

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    click,
    contains,
    dragenterFiles,
    dropFiles,
    insertText,
    isScrolledTo,
    nextAnimationFrame,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { DELAY_FOR_SPINNER } from "@mail/core/web/chatter";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import { file } from "@web/../tests/legacy/helpers/test_utils";

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
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-Thread");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/thread/data",
        "/mail/thread/messages",
    ]);
});

QUnit.test("can post a message on a record thread", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const { openFormView } = await start({
        mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step(route);
                const expected = {
                    context: args.context,
                    post_data: {
                        body: "hey",
                        attachment_ids: [],
                        attachment_tokens: [],
                        canned_response_ids: [],
                        message_type: "comment",
                        partner_emails: [],
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
    openFormView("res.partner", partnerId);
    await contains("button:contains(Send message)");
    await contains(".o-mail-Composer", 0);

    await click("button:contains(Send message)");
    await contains(".o-mail-Composer");

    await insertText(".o-mail-Composer-input", "hey");
    await contains(".o-mail-Message", 0);

    await click(".o-mail-Composer button:contains(Send):not(:disabled)");
    await contains(".o-mail-Message");
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
                    context: args.context,
                    post_data: {
                        attachment_ids: [],
                        attachment_tokens: [],
                        body: "hey",
                        canned_response_ids: [],
                        message_type: "comment",
                        partner_emails: [],
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
    openFormView("res.partner", partnerId);
    await contains("button:contains(Log note)");
    await contains(".o-mail-Composer", 0);

    await click("button:contains(Log note)");
    await contains(".o-mail-Composer");

    await insertText(".o-mail-Composer-input", "hey");
    await contains(".o-mail-Message", 0);

    await click(".o-mail-Composer button:contains(Log):not(:disabled)");
    await contains(".o-mail-Message");
    assert.verifySteps(["/mail/message/post"]);
});

QUnit.test("No attachment loading spinner when creating records", async () => {
    const { openFormView } = await start();
    openFormView("res.partner");
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files'] .fa-spin", 0);
});

QUnit.test(
    "No attachment loading spinner when switching from loading record to creation of record",
    async () => {
        const { advanceTime, openFormView, pyEnv } = await start({
            hasTimeControl: true,
            async mockRPC(route) {
                if (route === "/mail/thread/data") {
                    await new Promise(() => {});
                }
            },
        });
        const partnerId = pyEnv["res.partner"].create({ name: "John" });
        openFormView("res.partner", partnerId, { waitUntilDataLoaded: false });
        await contains("button[aria-label='Attach files']");
        await advanceTime(DELAY_FOR_SPINNER);
        await contains("button[aria-label='Attach files'] .fa-spin");
        await click(".o_form_button_create:eq(0)");
        await contains("button[aria-label='Attach files'] .fa-spin", 0);
    }
);

QUnit.test("Composer toggle state is kept when switching from aside to bottom", async () => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await contains(".o-mail-Form-chatter.o-aside .o-mail-Composer-input");
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
});

QUnit.test("Textarea content is kept when switching from aside to bottom", async () => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await contains(".o-mail-Form-chatter.o-aside .o-mail-Composer-input");
    await insertText(".o-mail-Composer-input", "Hello world !");
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
    await contains(".o-mail-Composer-input", 1, { value: "Hello world !" });
});

QUnit.test("Composer type is kept when switching from aside to bottom", async (assert) => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    openFormView("res.partner", partnerId);
    await click("button:contains(Log note)");
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
    assert.hasClass(
        $("button:contains(Log note)"),
        "btn-primary",
        "Active button should be the log note button"
    );
    assert.doesNotHaveClass($("button:contains(Send message)"), "btn-primary");
});

QUnit.test("chatter: drop attachments", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
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
    await afterNextRender(() => dragenterFiles($(".o-mail-Chatter")[0]));
    await contains(".o-mail-Dropzone");
    await contains(".o-mail-AttachmentCard", 0);

    await afterNextRender(() => dropFiles($(".o-mail-Dropzone")[0], files));
    await contains(".o-mail-AttachmentCard", 2);

    await afterNextRender(() => dragenterFiles($(".o-mail-Chatter")[0]));
    files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
    ];
    await afterNextRender(() => dropFiles($(".o-mail-Dropzone")[0], files));
    await contains(".o-mail-AttachmentCard", 3);
});

QUnit.test("should display subject when subject isn't infered from the record", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
        subject: "Salutations, voyageur",
    });
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Message:contains(Subject: Salutations, voyageur)");
});

QUnit.test("should not display user notification messages in chatter", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        message_type: "user_notification",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Thread-empty");
    await contains(".o-mail-Message", 0);
});

QUnit.test('post message with "CTRL-Enter" keyboard shortcut in chatter', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click("button:contains(Send message)");
    await contains(".o-mail-Message", 0);
    await insertText(".o-mail-Composer-input", "Test");
    triggerHotkey("control+Enter");
    await contains(".o-mail-Message");
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
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-AttachmentBox", 0);
    await contains(".o-mail-Thread");
    await contains(".o-mail-Message", 30);
});

QUnit.test("base rendering when chatter has no record", async (assert) => {
    const { openView } = await start();
    openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-AttachmentBox", 0);
    await contains(".o-mail-Chatter .o-mail-Thread");
    await contains(".o-mail-Message");
    assert.strictEqual($(".o-mail-Message-body").text(), "Creating a new record...");
    await contains("button:contains(Load More)", 0);
    await contains(".o-mail-Message-actions");
    await contains(".o-mail-Message-actions i", 0);
});

QUnit.test("base rendering when chatter has attachments", async () => {
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
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-AttachmentBox", 0);
});

QUnit.test("show attachment box", async () => {
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
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files']:contains(2)");
    await contains(".o-mail-AttachmentBox", 0);

    await click("button[aria-label='Attach files']");
    await contains(".o-mail-AttachmentBox");
});

QUnit.test("composer show/hide on log note/send message [REQUIRE FOCUS]", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button:contains(Send message)");
    await contains("button:contains(Log note)");
    await contains(".o-mail-Composer", 0);

    await click("button:contains(Send message)");
    await contains(".o-mail-Composer");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);

    await click("button:contains(Log note)");
    await contains(".o-mail-Composer");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);

    await click("button:contains(Log note)");
    await contains(".o-mail-Composer", 0);

    await click("button:contains(Send message)");
    await contains(".o-mail-Composer");

    await click("button:contains(Send message)");
    await contains(".o-mail-Composer", 0);
});

QUnit.test('do not post message with "Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click("button:contains(Send message)");
    await contains(".o-mail-Message", 0);
    await insertText(".o-mail-Composer-input", "Test");
    triggerHotkey("Enter");
    // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", 0);
});

QUnit.test("should not display subject when subject is the same as the thread name", async () => {
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
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Message:not(:contains(Salutations, voyageur))");
});

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
    openFormView("res.partner", partnerId_1);
    await contains(".o_breadcrumb:contains(Harry Potter)");
    await contains(".o-mail-Chatter");
    /**
     * The nextAnimationFrame is necessary because otherwise useAutoScroll would
     * set the scroll to bottom after the manually set value from this test.
     */
    await nextAnimationFrame();
    const scrolltop_1 = $(".o-mail-Chatter")[0].scrollHeight / 2;
    $(".o-mail-Chatter")[0].scrollTo({ top: scrolltop_1 });
    openFormView("res.partner", partnerId_2);
    await contains(".o_breadcrumb:contains(Ron Weasley)");
    /**
     * The nextAnimationFrame is necessary because otherwise useAutoScroll would
     * set the scroll to bottom after the manually set value from this test.
     */
    await nextAnimationFrame();
    const scrolltop_2 = $(".o-mail-Chatter")[0].scrollHeight / 3;
    $(".o-mail-Chatter")[0].scrollTo({ top: scrolltop_2 });
    openFormView("res.partner", partnerId_1);
    await contains(".o_breadcrumb:contains(Harry Potter)");
    /**
     * The nextAnimationFrame is necessary to give time for scroll to be restored.
     */
    await nextAnimationFrame();
    assert.ok(isScrolledTo($(".o-mail-Chatter")[0], scrolltop_1));
    openFormView("res.partner", partnerId_2);
    await contains(".o_breadcrumb:contains(Ron Weasley)");
    /**
     * The nextAnimationFrame is necessary to give time for scroll to be restored.
     */
    await nextAnimationFrame();
    assert.ok(isScrolledTo($(".o-mail-Chatter")[0], scrolltop_2));
});

QUnit.test("basic chatter rendering", async () => {
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
    openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
});

QUnit.test("basic chatter rendering without activities", async () => {
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
    openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains("button[aria-label='Attach files']");
    await contains("button:contains(Activities)", 0);
    await contains(".o-mail-Followers");
    await contains(".o-mail-Thread");
});

QUnit.test(
    'chatter just contains "creating a new record" message during the creation of a new record after having displayed a chatter for an existing record',
    async () => {
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
        openView({
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
        await click(".o_form_button_create:eq(0)");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message-body:contains(Creating a new record...)");
    }
);

QUnit.test(
    "should not display subject when subject is the same as the default subject",
    async () => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.fake",
            res_id: fakeId,
            subject: "Custom Default Subject", // default subject for res.fake, set on the model
        });
        const { openFormView } = await start();
        openFormView("res.fake", fakeId);
        await contains(".o-mail-Message:not(:contains(Custom Default Subject))");
    }
);

QUnit.test(
    "should not display subject when subject is the same as the thread name with custom default subject",
    async () => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.fake",
            res_id: fakeId,
            subject: "Salutations, voyageur",
        });
        const { openFormView } = await start();
        openFormView("res.fake", fakeId);
        await contains(".o-mail-Message:not(:contains(Custom Default Subject))");
    }
);

QUnit.test("basic chatter rendering without followers", async () => {
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
                    <!-- no message_follower_ids field -->
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains("button[aria-label='Attach files']");
    await contains("button:contains(Activities)");
    await contains(".o-mail-Chatter .o-mail-Thread");
    await contains(".o-mail-Followers", 0);
});

QUnit.test("basic chatter rendering without messages", async () => {
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
                    <!-- no message_ids field -->
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views } });
    openView({
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains("button[aria-label='Attach files']");
    await contains("button:contains(Activities)");
    await contains(".o-mail-Followers");
    await contains(".o-mail-Chatter .o-mail-Thread", 0);
});

QUnit.test("chatter updating", async () => {
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
    openFormView("res.partner", partnerId_1, {
        props: { resIds: [partnerId_1, partnerId_2] },
    });
    await click(".o_pager_next");
    await contains(".o-mail-Message");
});

QUnit.test("post message on draft record", async () => {
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
    openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await click("button:contains(Send message)");
    await insertText(".o-mail-Composer-input", "Test");
    await click(".o-mail-Composer button:contains(Send):not(:disabled)");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message:contains(Test)");
});

QUnit.test(
    "schedule activities on draft record should prompt with scheduling an activity (proceed with action)",
    async () => {
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
        const { openFormView } = await start({ serverData: { views } });
        openFormView("res.partner");
        await click("button:contains(Activities)");
        await contains(".o_dialog:contains(Schedule Activity)");
    }
);

QUnit.test("upload attachment on draft record", async () => {
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
    openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    const [chatter, file] = await Promise.all([
        contains(".o-mail-Chatter"),
        createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ]);
    await contains(".button[aria-label='Attach files']:contains(1)", 0);
    dragenterFiles(chatter[0]);
    dropFiles((await contains(".o-mail-Dropzone"))[0], [file]);
    await contains("button[aria-label='Attach files']:contains(1)");
});

QUnit.test("Follower count of draft record is set to 0", async (assert) => {
    const { openView } = await start();
    await openView({ res_model: "res.partner", views: [[false, "form"]] });
    await contains(".o-mail-Followers:contains(0)");
});
