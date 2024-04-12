import {
    SIZES,
    assertSteps,
    click,
    contains,
    createFile,
    defineMailModels,
    dragenterFiles,
    dropFiles,
    insertText,
    onRpcBefore,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { DELAY_FOR_SPINNER } from "@mail/chatter/web_portal/chatter";
import { describe, expect, getFixture, test } from "@odoo/hoot";
import { Deferred, advanceTime } from "@odoo/hoot-mock";
import { mockService, onRpc, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("simple chatter on a record", async () => {
    const pyEnv = await startServer();
    onRpcBefore((route, args) => {
        if (route.startsWith("/mail") || route.startsWith("/discuss")) {
            step(`${route} - ${JSON.stringify(args)}`);
        }
    });
    await start();
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-Thread");
    await assertSteps([
        `/mail/thread/data - {"request_list":["followers","attachments","suggestedRecipients"],"thread_id":${partnerId},"thread_model":"res.partner"}`,
        `/mail/thread/messages - {"thread_id":${partnerId},"thread_model":"res.partner","limit":30}`,
    ]);
});

test("can post a message on a record thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    onRpcBefore("/mail/message/post", (args) => {
        step("/mail/message/post");
        const expected = {
            context: args.context,
            post_data: {
                body: "hey",
                attachment_ids: [],
                message_type: "comment",
                partner_ids: [],
                subtype_xmlid: "mail.mt_comment",
            },
            canned_response_ids: [],
            attachment_tokens: [],
            partner_additional_values: {},
            partner_emails: [],
            thread_id: partnerId,
            thread_model: "res.partner",
        };
        expect(args).toEqual(expected);
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });
    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer");
    await insertText(".o-mail-Composer-input", "hey");
    await contains(".o-mail-Message", { count: 0 });
    await click(".o-mail-Composer button:enabled", { text: "Send" });
    await contains(".o-mail-Message");
    await assertSteps(["/mail/message/post"]);
});

test("can post a note on a record thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    onRpcBefore("/mail/message/post", (args) => {
        step("/mail/message/post");
        const expected = {
            context: args.context,
            post_data: {
                attachment_ids: [],
                body: "hey",
                message_type: "comment",
                partner_ids: [],
                subtype_xmlid: "mail.mt_note",
            },
            attachment_tokens: [],
            canned_response_ids: [],
            partner_additional_values: {},
            partner_emails: [],
            thread_id: partnerId,
            thread_model: "res.partner",
        };
        expect(args).toEqual(expected);
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });
    await click("button", { text: "Log note" });
    await contains(".o-mail-Composer");
    await insertText(".o-mail-Composer-input", "hey");
    await contains(".o-mail-Message", { count: 0 });
    await click(".o-mail-Composer button:enabled", { text: "Log" });
    await contains(".o-mail-Message");
    await assertSteps(["/mail/message/post"]);
});

test("No attachment loading spinner when creating records", async () => {
    await start();
    await openFormView("res.partner");
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files'] .fa-spin", { count: 0 });
});

test("No attachment loading spinner when switching from loading record to creation of record", async () => {
    onRpc("/mail/thread/data", async () => await new Deferred());
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    await openFormView("res.partner", partnerId);
    await contains("button[aria-label='Attach files']");
    await advanceTime(DELAY_FOR_SPINNER);
    await contains("button[aria-label='Attach files'] .fa-spin");
    await click(".o_control_panel_collapsed_create .o_form_button_create");
    await contains("button[aria-label='Attach files'] .fa-spin", { count: 0 });
});

test("Composer toggle state is kept when switching from aside to bottom", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-Form-chatter.o-aside .o-mail-Composer-input");
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
});

test("Textarea content is kept when switching from aside to bottom", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-Form-chatter.o-aside .o-mail-Composer-input");
    await insertText(".o-mail-Composer-input", "Hello world !");
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
    await contains(".o-mail-Composer-input", { value: "Hello world !" });
});

test("Composer type is kept when switching from aside to bottom", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Log note" });
    patchUiSize({ size: SIZES.LG });
    window.dispatchEvent(new Event("resize"));
    await contains(".o-mail-Form-chatter:not(.o-aside) .o-mail-Composer-input");
    await contains("button.btn-primary", { text: "Log note" });
    await contains("button:not(.btn-primary)", { text: "Send message" });
});

test("chatter: drop attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
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

test("chatter: drop attachment should refresh thread data with hasParentReloadOnAttachmentsChange prop", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});

    onRpc(async ({ route }) => {
        if (route === "/mail/attachment/upload") {
            const attachmentId = pyEnv["ir.attachment"].create([
                { res_id: partnerId, res_model: "res.partner", mimetype: "application/pdf" },
            ]);
            pyEnv["res.partner"].write([partnerId], { message_main_attachment_id: attachmentId });
        }
    });
    await start();
    const target = getFixture();
    target.classList.add("o_web_client");

    await openFormView("res.partner", partnerId, {
        arch: `
            <form>
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview" />
                <chatter reload_on_post="True" reload_on_attachment="True"/>
            </form>`,
    });
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

test("should display subject when subject isn't infered from the record", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
        subject: "Salutations, voyageur",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { text: "Subject: Salutations, voyageurnot empty" });
});

test("should not display user notification messages in chatter", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        message_type: "user_notification",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
});

test('post message with "CTRL-Enter" keyboard shortcut in chatter', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-Message", { count: 0 });
    await insertText(".o-mail-Composer-input", "Test");
    triggerHotkey("control+Enter");
    await contains(".o-mail-Message");
});

test("base rendering when chatter has no attachment", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-AttachmentBox", { count: 0 });
    await contains(".o-mail-Thread");
    await contains(".o-mail-Message", { count: 30 });
});

test("base rendering when chatter has no record", async () => {
    await start();
    await openFormView("res.partner");
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

test("base rendering when chatter has attachments", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains(".o-mail-AttachmentBox", { count: 0 });
});

test("show attachment box", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files']", { text: "2" });
    await contains(".o-mail-AttachmentBox", { count: 0 });
    await click("button[aria-label='Attach files']");
    await contains(".o-mail-AttachmentBox");
});

test("composer show/hide on log note/send message [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button", { text: "Send message" });
    await contains("button", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });
    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer");
    expect(".o-mail-Composer-input").toBeFocused();
    await click("button", { text: "Log note" });
    await contains(".o-mail-Composer");
    expect(".o-mail-Composer-input").toBeFocused();
    await click("button", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });
    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer");
    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });
});

test('do not post message with "Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-Message", { count: 0 });
    await insertText(".o-mail-Composer-input", "Test");
    triggerHotkey("Enter");
    // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", { count: 0 });
});

test("should not display subject when subject is the same as the thread name", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { text: "not empty" });
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Salutations, voyageurnot empty",
    });
});

test("scroll position is kept when navigating from one record to another", async () => {
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
    await start();
    await openFormView("res.partner", partnerId_1);
    await contains(".o-mail-Message", { count: 20 });
    const scrollValue1 = $(".o-mail-Chatter")[0].scrollHeight / 2;
    await contains(".o-mail-Chatter", { scroll: 0 });
    await scroll(".o-mail-Chatter", scrollValue1);
    await openFormView("res.partner", partnerId_2);
    await contains(".o-mail-Message", { count: 30 });
    const scrollValue2 = $(".o-mail-Chatter")[0].scrollHeight / 3;
    await scroll(".o-mail-Chatter", scrollValue2);
    await openFormView("res.partner", partnerId_1);
    await contains(".o-mail-Message", { count: 20 });
    await contains(".o-mail-Chatter", { scroll: scrollValue1 });
    await openFormView("res.partner", partnerId_2);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Chatter", { scroll: scrollValue2 });
});

test("basic chatter rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "second partner" });
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
    });
    await contains(".o-mail-Chatter");
});

test('chatter just contains "creating a new record" message during the creation of a new record after having displayed a chatter for an existing record', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const views = {
        "res.partner,false,form": `
                <form string="Partners">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                    <chatter/>
                </form>`,
    };
    await start({ serverData: { views } });
    await openFormView("res.partner", partnerId);
    await click(".o_control_panel_collapsed_create .o_form_button_create");
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-body", { text: "Creating a new record..." });
});

test("should display subject when subject is not the same as the default subject", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.fake",
        res_id: fakeId,
        subject: "Another Subject",
    });
    await start();
    await openFormView("res.fake", fakeId);
    await contains(".o-mail-Message", { text: "Subject: Another Subjectnot empty" });
});

test("should not display subject when subject is the same as the default subject", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.fake",
        res_id: fakeId,
        subject: "Custom Default Subject",
    });
    await start();
    await openFormView("res.fake", fakeId);
    await contains(".o-mail-Message", { text: "not empty" });
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Custom Default Subjectnot empty",
    });
});

test("should not display subject when subject is the same as the thread name with custom default subject", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.fake",
        res_id: fakeId,
        subject: "Salutations, voyageur",
    });
    await start();
    await openFormView("res.fake", fakeId);
    await contains(".o-mail-Message", { text: "not empty" });
    await contains(".o-mail-Message", {
        count: 0,
        text: "Subject: Custom Default Subjectnot empty",
    });
});

test("chatter updating", async () => {
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
    await start();
    await openFormView("res.partner", partnerId_1, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
        resIds: [partnerId_1, partnerId_2],
    });
    await click(".o_pager_next");
    await contains(".o-mail-Message");
});

test("post message on draft record", async () => {
    await start();
    await openFormView("res.partner", undefined, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
    });
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "Test");
    await click(".o-mail-Composer button:enabled", { text: "Send" });
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-content", { text: "Test" });
});

test("schedule activities on draft record should prompt with scheduling an activity (proceed with action)", async () => {
    const wizardOpened = new Deferred();
    mockService("action", {
        doAction(action, options) {
            if (action.res_model === "res.partner") {
                return super.doAction(...arguments);
            } else if (action.res_model === "mail.activity.schedule") {
                step("mail.activity.schedule");
                expect(action.context.active_model).toBe("res.partner");
                expect(Number(action.context.active_id)).toBeGreaterThan(0);
                options.onClose();
                wizardOpened.resolve();
            } else {
                step("Unexpected action" + action.res_model);
            }
        },
    });
    await start();
    await openFormView("res.partner", undefined, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
    });
    await click("button", { text: "Activities" });
    await wizardOpened;
    await assertSteps(["mail.activity.schedule"]);
});

test("upload attachment on draft record", async () => {
    await start();
    await openFormView("res.partner", undefined, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
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

test("Follower count of draft record is set to 0", async () => {
    await start();
    await openFormView("res.partner");
    await contains(".o-mail-Followers", { text: "0" });
});

test("Mentions in composer should still work when using pager", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { display_name: "Partner 1" },
        { display_name: "Partner 2" },
    ]);
    patchUiSize({ size: SIZES.LG });
    await start();
    await openFormView("res.partner", partnerId_1, { resIds: [partnerId_1, partnerId_2] });
    await click("button", { text: "Log note" });
    await click(".o_pager_next");
    await insertText(".o-mail-Composer-input", "@");
    // all records in DB: Mitchell Admin | Hermit | Public user except OdooBot
    await contains(".o-mail-Composer-suggestion", { count: 3 });
});
