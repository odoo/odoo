import {
    SIZES,
    click,
    contains,
    defineMailModels,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, expect } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test.skip("Form view not scrolled when switching record", async () => {
    // FIXME: test passed in test environment but in practice scroll are reset to 0
    // HOOT matches behaviour in prod and shows tests not passing as expected
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        {
            description: [...Array(60).keys()].join("\n"),
            display_name: "Partner 1",
        },
        {
            description: [...Array(60).keys()].join("\n"),
            display_name: "Partner 2",
        },
    ]);
    const messages = [...Array(60).keys()].map((id) => {
        return {
            body: "not empty",
            model: "res.partner",
            res_id: id < 29 ? partnerId_1 : partnerId_2,
        };
    });
    pyEnv["mail.message"].create(messages);
    patchUiSize({ size: SIZES.LG });
    await start();
    await openFormView("res.partner", partnerId_1, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <chatter/>
            </form>`,
        resIds: [partnerId_1, partnerId_2],
    });
    await contains(".o-mail-Message", { count: 29 });
    await contains(".o_content", { scroll: 0 });
    await scroll(".o_content", 150);
    await click(".o_pager_next");
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o_content", { scroll: 150 });
    await scroll(".o_content", 0);
    await click(".o_pager_previous");
    await contains(".o-mail-Message", { count: 29 });
    await contains(".o_content", { scroll: 0 });
});

test("Attachments that have been unlinked from server should be visually unlinked from record", async () => {
    // Attachments that have been fetched from a record at certain time and then
    // removed from the server should be reflected on the UI when the current
    // partner accesses this record again.
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { display_name: "Partner1" },
        { display_name: "Partner2" },
    ]);
    const [attachmentId_1] = pyEnv["ir.attachment"].create([
        {
            mimetype: "text.txt",
            res_id: partnerId_1,
            res_model: "res.partner",
        },
        {
            mimetype: "text.txt",
            res_id: partnerId_1,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId_1, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
        resId: partnerId_1,
        resIds: [partnerId_1, partnerId_2],
    });
    await contains("button[aria-label='Attach files']", { text: "2" });
    // The attachment links are updated on (re)load,
    // so using pager is a way to reload the record "Partner1".
    await click(".o_pager_next");
    await contains("button[aria-label='Attach files']:not(:has(sup))");
    // Simulate unlinking attachment 1 from Partner 1.
    pyEnv["ir.attachment"].write([attachmentId_1], { res_id: 0 });
    await click(".o_pager_previous");
    await contains("button[aria-label='Attach files']", { text: "1" });
});

test("ellipsis button is not duplicated when switching from read to edit mode", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        author_id: partnerId,
        // "data-o-mail-quote" added by server is intended to be compacted in ellipsis block
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <div data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </div>
            </div>`,
        model: "res.partner",
        res_id: partnerId,
    });
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
    await contains(".o-mail-Message");
    await contains(".o-mail-ellipsis");
});

test("[TECHNICAL] unfolded ellipsis button should not fold on message click besides that button", async () => {
    // message click triggers a re-render. Before writing of this test, the
    // insertion of ellipsis button were done during render. This meant
    // any re-render would re-insert the ellipsis button. If some buttons
    // were unfolded, any re-render would fold them again.
    //
    // This previous behavior is undesirable, and results to bothersome UX
    // such as inability to copy/paste unfolded message content due to click
    // from text selection automatically folding all ellipsis buttons.
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "Someone" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        // "data-o-mail-quote" added by server is intended to be compacted in ellipsis block
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>`,
        model: "res.partner",
        res_id: partnerId,
    });
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
    expect(".o-mail-Message-body span").toHaveCount(0);
    await click(".o-mail-ellipsis");
    expect(".o-mail-Message-body span").toHaveText('--\nSystem')
    await click(".o-mail-Message");
    expect(".o-mail-Message-body span").toHaveCount(1);
});

test("ellipsis button on message of type notification", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        author_id: partnerId,
        // "data-o-mail-quote" enables ellipsis block
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>`,
        model: "res.partner",
        res_id: partnerId,
        message_type: "notification",
    });
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
    await contains(".o-mail-ellipsis");
});
