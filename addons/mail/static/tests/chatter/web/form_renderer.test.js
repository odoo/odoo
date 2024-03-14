import { describe, test } from "@odoo/hoot";
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
} from "../../mail_test_helpers";

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

test("read more/less links are not duplicated when switching from read to edit mode", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        author_id: partnerId,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
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
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Message");
    await contains(".o-mail-read-more-less");
});

test("read more links becomes read less after being clicked", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
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
        },
    ]);
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
    await contains(".o-mail-read-more-less", { text: "Read More" });
    await click(".o-mail-read-more-less");
    await contains(".o-mail-read-more-less", { text: "Read Less" });
});

test("[TECHNICAL] unfolded read more/less links should not fold on message click besides those button links", async () => {
    // message click triggers a re-render. Before writing of this test, the
    // insertion of read more/less links were done during render. This meant
    // any re-render would re-insert the read more/less links. If some button
    // links were unfolded, any re-render would fold them again.
    //
    // This previous behavior is undesirable, and results to bothersome UX
    // such as inability to copy/paste unfolded message content due to click
    // from text selection automatically folding all read more/less links.
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "Someone" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
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
    await contains(".o-mail-read-more-less", { text: "Read More" });
    await click(".o-mail-read-more-less");
    await contains(".o-mail-read-more-less", { text: "Read Less" });
    await click(".o-mail-Message");
    await contains(".o-mail-read-more-less", { text: "Read Less" });
});

test("read more/less links on message of type notification", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        author_id: partnerId,
        // "data-o-mail-quote" enables read more/less blocks
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
    await contains(".o-mail-Message a", { text: "Read More" });
});
