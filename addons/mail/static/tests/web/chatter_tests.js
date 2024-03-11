/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { DELAY_FOR_SPINNER } from "@mail/core/web/chatter";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { getFixture, makeDeferred, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import {
    click,
    contains,
    createFile,
    dragenterFiles,
    dropFiles,
    insertText,
    scroll,
} from "@web/../tests/utils";

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
                        partner_additional_values: {},
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
    await contains("button", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });

    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer");

    await insertText(".o-mail-Composer-input", "hey");
    await contains(".o-mail-Message", { count: 0 });

    await click(".o-mail-Composer button:enabled", { text: "Send" });
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
                        partner_additional_values: {},
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
    await contains("button", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });

    await click("button", { text: "Log note" });
    await contains(".o-mail-Composer");

    await insertText(".o-mail-Composer-input", "hey");
    await contains(".o-mail-Message", { count: 0 });

    await click(".o-mail-Composer button:enabled", { text: "Log" });
    await contains(".o-mail-Message");
    assert.verifySteps(["/mail/message/post"]);
});

QUnit.test("No attachment loading spinner when creating records", async () => {
    const { openFormView } = await start();
    openFormView("res.partner");
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files'] .fa-spin", { count: 0 });
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
        openFormView("res.partner", partnerId);
        await contains("button[aria-label='Attach files']");
        await advanceTime(DELAY_FOR_SPINNER);
        await contains("button[aria-label='Attach files'] .fa-spin");
        await click(".o_control_panel_collapsed_create .o_form_button_create");
        await contains("button[aria-label='Attach files'] .fa-spin", { count: 0 });
    }
);

QUnit.test("Composer toggle state is kept when switching from aside to bottom", async () => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
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
    await click("button", { text: "Send message" });
    await contains(".o-mail-Form-chatter.o-aside .o-mail-Composer-input");
    await insertText(".o-mail-Composer-input", "Hello world !");
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
    await contains(".o-mail-Composer-input", { value: "Hello world !" });
});

QUnit.test("Composer type is kept when switching from aside to bottom", async () => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    openFormView("res.partner", partnerId);
    await click("button", { text: "Log note" });
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
    await contains("button.btn-primary", { text: "Log note" });
    await contains("button:not(.btn-primary)", { text: "Send message" });
});

QUnit.test("chatter: drop attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    const files = [
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
    await dragenterFiles(".o-mail-Chatter", files);
    await contains(".o-mail-Dropzone");
    await contains(".o-mail-AttachmentCard", { count: 0 });
    await dropFiles(".o-mail-Dropzone", files);
    await contains(".o-mail-AttachmentCard", { count: 2 });
    const extraFiles = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
    ];
    await dragenterFiles(".o-mail-Chatter", extraFiles);
    await dropFiles(".o-mail-Dropzone", extraFiles);
    await contains(".o-mail-AttachmentCard", { count: 3 });
});

QUnit.test("chatter: drop attachment should refresh thread data with hasParentReloadOnAttachmentsChange prop", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const views = {
        "res.partner,false,form": `
            <form>
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview" />
                <div class="oe_chatter">
                    <field name="message_main_attachment_id" invisible="1" on_change="1" />
                    <field name="message_ids" options="{'post_refresh': 'always'}"/>
                </div>
            </form>`,
    };
    const target = getFixture();
    target.classList.add("o_web_client");
    const { openFormView } = await start({
        serverData: { views },
        target,
        async mockRPC(route) {
            if (route === "/mail/attachment/upload") {
                const attachmentId = pyEnv["ir.attachment"].create([
                    { res_id: partnerId, res_model: "res.partner", mimetype: "application/pdf" }
                ]);
                pyEnv["res.partner"].write([partnerId], { message_main_attachment_id: attachmentId });
                return Promise.resolve();
            }
        },
    });
    await openFormView("res.partner", partnerId);
    const files = [
        await createFile({
            contentType: "application/pdf",
            name: "text.pdf",
        }),
    ];
    await dragenterFiles(".o-mail-Chatter", files);
    await dropFiles(".o-mail-Dropzone", files);
    await contains(".o-mail-Attachment iframe", { count: 1 });
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
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
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
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
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
    await click("button", { text: "Send message" });
    await contains(".o-mail-Message", { count: 0 });
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
    await contains(".o-mail-AttachmentBox", { count: 0 });
    await contains(".o-mail-Thread");
    await contains(".o-mail-Message", { count: 30 });
});

QUnit.test("base rendering when chatter has no record", async () => {
    const { openView } = await start();
    openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-AttachmentBox", { count: 0 });
    await contains(".o-mail-Chatter .o-mail-Thread");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-author", { text: "Mitchell Admin" });
    await contains(".o-mail-Message-body", { text: "Creating a new record..." });
    await contains("button", { count: 0, text: "Load More" });
    await contains(".o-mail-Message-actions");
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
    await contains(".o-mail-AttachmentBox", { count: 0 });
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
    await contains("button[aria-label='Attach files']", { text: "2" });
    await contains(".o-mail-AttachmentBox", { count: 0 });

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
    await contains("button", { text: "Send message" });
    await contains("button", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });

    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);

    await click("button", { text: "Log note" });
    await contains(".o-mail-Composer");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);

    await click("button", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });

    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer");

    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });
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
    await click("button", { text: "Send message" });
    await contains(".o-mail-Message", { count: 0 });
    await insertText(".o-mail-Composer-input", "Test");
    triggerHotkey("Enter");
    // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", { count: 0 });
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
    await contains(".o-mail-Message", { text: "not empty" });
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

QUnit.test("scroll position is kept when navigating from one record to another", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({ name: "Harry Potter" });
    const partnerId_2 = pyEnv["res.partner"].create({ name: "Ron Weasley" });
    // Fill both channels with random messages in order for the scrollbar to
    // appear.
    pyEnv["mail.message"].create(
        Array(50)
            .fill(0)
            .map((_, index) => ({
                body: "Non Empty Body ".repeat(25),
                model: "res.partner",
                res_id: index < 20 ? partnerId_1 : partnerId_2,
            }))
    );
    const { openFormView } = await start();
    openFormView("res.partner", partnerId_1);
    await contains(".o-mail-Message", { count: 20 });
    const scrollValue1 = $(".o-mail-Chatter")[0].scrollHeight / 2;
    await contains(".o-mail-Chatter", { scroll: 0 });
    await scroll(".o-mail-Chatter", scrollValue1);
    openFormView("res.partner", partnerId_2);
    await contains(".o-mail-Message", { count: 30 });
    const scrollValue2 = $(".o-mail-Chatter")[0].scrollHeight / 3;
    await scroll(".o-mail-Chatter", scrollValue2);
    openFormView("res.partner", partnerId_1);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Chatter", { scroll: scrollValue1 });
    openFormView("res.partner", partnerId_2);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Chatter", { scroll: scrollValue2 });
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
    await contains("button", { count: 0, text: "Activities" });

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
        await click(".o_control_panel_collapsed_create .o_form_button_create");
        await contains(".o-mail-Message");
        await contains(".o-mail-Message-body", { text: "Creating a new record..." });
    }
);

QUnit.test(
    "should display subject when subject is not the same as the default subject",
    async () => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.fake",
            res_id: fakeId,
            subject: "Another Subject",
        });
        const { openFormView } = await start();
        openFormView("res.fake", fakeId);
        await contains(".o-mail-Message", { text: "Subject: Another Subjectnot empty" });
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
            subject: "Custom Default Subject",
        });
        const { openFormView } = await start();
        openFormView("res.fake", fakeId);
        await contains(".o-mail-Message", { text: "not empty" });
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Custom Default Subjectnot empty",
        });
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
        await contains(".o-mail-Message", { text: "not empty" });
        await contains(".o-mail-Message", {
            count: 0,
            text: "Subject: Custom Default Subjectnot empty",
        });
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
    await contains("button", { text: "Activities" });
    await contains(".o-mail-Chatter .o-mail-Thread");
    await contains(".o-mail-Followers", { count: 0 });
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
    await contains("button", { text: "Activities" });
    await contains(".o-mail-Followers");
    await contains(".o-mail-Chatter .o-mail-Thread", { count: 0 });
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
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "Test");
    await click(".o-mail-Composer button:enabled", { text: "Send" });
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-content", { text: "Test" });
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
        const { env, openFormView } = await start({ serverData: { views } });
        const wizardOpened = makeDeferred();
        patchWithCleanup(env.services.action, {
            doAction(action, options) {
                if (action.res_model === "res.partner") {
                    return super.doAction(action, options);
                } else if (action.res_model === "mail.activity.schedule") {
                    assert.step("mail.activity.schedule");
                    assert.equal(action.context.active_model, "res.partner");
                    assert.ok(Number(action.context.active_id));
                    options.onClose();
                    wizardOpened.resolve();
                } else {
                    assert.step("Unexpected action" + action.res_model);
                }
            },
        });
        await openFormView("res.partner");
        await click("button", { text: "Activities" });
        await wizardOpened;
        assert.verifySteps(["mail.activity.schedule"]);
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
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files']", { count: 0, text: "1" });
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ];
    await dragenterFiles(".o-mail-Chatter", files);
    await dropFiles(".o-mail-Dropzone", files);
    await contains("button[aria-label='Attach files']", { text: "1" });
});

QUnit.test("Follower count of draft record is set to 0", async () => {
    const { openView } = await start();
    await openView({ res_model: "res.partner", views: [[false, "form"]] });
    await contains(".o-mail-Followers", { text: "0" });
});

QUnit.test("Mentions in composer should still work when using pager", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { display_name: "Partner 1" },
        { display_name: "Partner 2" },
    ]);
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
    patchUiSize({ size: SIZES.LG });
    const { openView } = await start({ serverData: { views } });
    await openView(
        {
            res_model: "res.partner",
            res_id: partnerId_1,
            views: [[false, "form"]],
        },
        { resIds: [partnerId_1, partnerId_2] }
    );

    await click("button", { text: "Log note" });
    await click(".o_pager_next");
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 2 });
});
