/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, scroll } from "@web/../tests/utils";

QUnit.module("Form renderer");

QUnit.test("Form view not scrolled when switching record", async () => {
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
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    patchUiSize({ size: SIZES.LG });
    const { openView } = await start({ serverData: { views } });
    openView(
        {
            res_model: "res.partner",
            res_id: partnerId_1,
            views: [[false, "form"]],
        },
        { resIds: [partnerId_1, partnerId_2] }
    );
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

QUnit.test(
    "Attachments that have been unlinked from server should be visually unlinked from record",
    async () => {
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
        openView(
            {
                res_model: "res.partner",
                res_id: partnerId_1,
                views: [[false, "form"]],
            },
            {
                resId: partnerId_1,
                resIds: [partnerId_1, partnerId_2],
            }
        );
        await contains("button[aria-label='Attach files']", { text: "2" });
        // The attachment links are updated on (re)load,
        // so using pager is a way to reload the record "Partner1".
        await click(".o_pager_next");
        await contains("button[aria-label='Attach files']:not(:has(sup))");
        // Simulate unlinking attachment 1 from Partner 1.
        pyEnv["ir.attachment"].write([attachmentId_1], { res_id: 0 });
        await click(".o_pager_previous");
        await contains("button[aria-label='Attach files']", { text: "1" });
    }
);

QUnit.test(
    "read more/less links are not duplicated when switching from read to edit mode",
    async () => {
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
        const openViewAction = {
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        };
        openView(openViewAction);
        await contains(".o-mail-Chatter");
        await contains(".o-mail-Message");
        await contains(".o-mail-read-more-less");
    }
);

QUnit.test("read more links becomes read less after being clicked", async (assert) => {
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
    const openViewAction = {
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    };
    openView(openViewAction);
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Message");
    await contains(".o-mail-read-more-less", { text: "Read More" });

    await click(".o-mail-read-more-less");
    await contains(".o-mail-read-more-less", { text: "Read Less" });
});

QUnit.test(
    "[TECHNICAL] unfolded read more/less links should not fold on message click besides those button links",
    async () => {
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
                </div>
            `,
            model: "res.partner",
            res_id: partnerId,
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
        const { openView } = await start({ serverData: { views } });
        openView({
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
        await contains(".o-mail-read-more-less", { text: "Read More" });

        await click(".o-mail-read-more-less");
        await contains(".o-mail-read-more-less", { text: "Read Less" });

        await click(".o-mail-Message");
        await contains(".o-mail-read-more-less", { text: "Read Less" });
    }
);

QUnit.test("read more/less links on message of type notification", async () => {
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
    const openViewAction = {
        res_model: "res.partner",
        res_id: partnerId,
        views: [[false, "form"]],
    };
    openView(openViewAction);
    await contains(".o-mail-Message a", { text: "Read More" });
});
