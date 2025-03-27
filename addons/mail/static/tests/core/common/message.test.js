import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { queryAllTexts } from "@odoo/hoot-dom";
import { describe, test, expect } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("following internal link from chatter does not open chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jeanne" });
    pyEnv["mail.message"].create({
        body: `Created by <a href="#" data-oe-model="res.partner" data-oe-id="${pyEnv.user.partner_id}">Admin</a>`,
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o_last_breadcrumb_item", { text: "Jeanne" });
    await click("a", { text: "Admin" });
    await contains(".o_last_breadcrumb_item", { text: "Mitchell Admin" });
    // Assert 0 chat windows not sufficient because not enough time for potential chat window opening.
    // Let's open another chat window to give some time and assert only manually open chat window opens.
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await insertText("input[placeholder='Search a conversation']", "abc");
    await click("a", { text: "Create Channel" });
    await contains(".o-mail-ChatWindow-header", { text: "abc" });
    await contains(".o-mail-ChatWindow", { count: 1 });
});

test("message reply container is visible by default and can be hidden", async () => {
    const pyEnv = await startServer();
    const messageBody = "First message";
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["mail.message"].create({
        body: messageBody,
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
        author_id: partnerId,
        email_from: "testpartner@odoo.com",
    });
    const partner = pyEnv["res.partner"].browse(partnerId);
    pyEnv["mail.message"].create({
        body: `
            <div>Hello</div>
            <div class="o_mail_reply_container" data-o-mail-quote="1">
                <div class="o_mail_reply_content">
                    <blockquote>
                        <div>${messageBody}</div>
                    </blockquote>
                    <span data-o-mail-quote="1">
                    On Thu, May 22, 2025 at 10:17 AM ${partner[0].name}
                    </span>
                    <a target="_blank" href="mailto:${partner[0].email}" data-o-mail-quote="1">${partner[0].email}</a>
                    wrote
                </div>
            </div>
            `,
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
        author_id: partnerId,
        email_from: "testpartner@odoo.com",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-ellipsis");
    await expect(".o_mail_reply_content").toBeVisible();
    await click(".o-mail-ellipsis");
    await expect(".o_mail_reply_content").not.toBeVisible();
    await click(".o-mail-ellipsis");
    await expect(".o_mail_reply_content").toBeVisible();
    const children = Array.from(
        document.querySelector(".o_mail_reply_container .o_mail_reply_content").children
    );
    expect(children.length).toEqual(3);
    // check structure
    expect(children.map((el) => el.tagName)).toEqual(["BLOCKQUOTE", "SPAN", "A"]);
    // check content
    expect(queryAllTexts(children)).toEqual(["First message", "On Thu, May 22, 2025 at 10:17 AM TestPartner", "testpartner@odoo.com"]);
    expect(children[2].href.includes("mailto:testpartner@odoo.com")).toBe(true);
});
