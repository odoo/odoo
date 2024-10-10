import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { describe, test, expect } from "@odoo/hoot";
import { queryOne, waitUntil } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    click,
    contains,
    openFormView,
    registerArchs,
    start,
    startServer,
    patchUiSize,
    SIZES,
} from "@mail/../tests/mail_test_helpers";
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineTestMailModels();

test("Attachment view popout controls test", async () => {
    /*
     * This test makes sure that the attachment view controls are working in the following cases:
     * - Before opening the popout window
     * - Inside the popout window
     * - After closing the popout window
     */
    const popoutIframe = document.createElement("iframe");
    const popoutWindow = {
        closed: false,
        get document() {
            const doc = popoutIframe.contentDocument;
            const originalWrite = doc.write;
            doc.write = (content) => {
                // This avoids duplicating the test script in the popoutWindow
                const sanitizedContent = content.replace(
                    /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
                    ""
                );
                originalWrite.call(doc, sanitizedContent);
            };
            return doc;
        },
        get body() {
            return popoutWindow.document.querySelector(".o-mail-PopoutAttachmentView");
        },
        close: () => {
            popoutWindow.closed = true;
            popoutIframe.remove(popoutWindow.body);
        },
        popoutContains: async (selector) => {
            await animationFrame();
            await waitUntil(() => popoutWindow.body);
            const target = popoutWindow.body.querySelector(selector);
            expect(target).toBeDisplayed();
            return target;
        },
        popoutClick: async (selector) => {
            const target = await popoutWindow.popoutContains(selector);
            click(target);
        },
    };
    patchWithCleanup(browser, {
        open: () => {
            queryOne(".o_popout_holder").append(popoutIframe);
            return popoutWindow;
        },
    });

    const pyEnv = await startServer();
    const recordId = pyEnv["mail.test.simple.main.attachment"].create({
        display_name: "first partner",
        message_attachment_count: 2,
    });
    const attachmentIds = pyEnv["ir.attachment"].create([
        {
            mimetype: "image/jpeg",
            res_id: recordId,
            res_model: "mail.test.simple.main.attachment",
        },
        {
            mimetype: "application/pdf",
            res_id: recordId,
            res_model: "mail.test.simple.main.attachment",
        },
    ]);
    pyEnv["mail.message"].create({
        attachment_ids: attachmentIds,
        model: "mail.test.simple.main.attachment",
        res_id: recordId,
    });
    registerArchs({
        "mail.test.simple.main.attachment,false,form": `
                <form string="Test document">
                    <div class="o_popout_holder"/>
                    <sheet>
                        <field name="name"/>
                    </sheet>
                    <div class="o_attachment_preview"/>
                    <chatter/>
                </form>`,
    });

    patchUiSize({ size: SIZES.XXL });
    await start();
    await openFormView("mail.test.simple.main.attachment", recordId);
    await click(".o_attachment_preview .o_move_next");
    await contains(".o_attachment_preview img");
    await click(".o_attachment_preview .o_move_previous");
    await contains(".o_attachment_preview iframe");
    await click(".o_attachment_preview .o_attachment_control");
    await animationFrame();
    expect(".o_attachment_preview").not.toBeVisible();
    await popoutWindow.popoutClick(".o_move_next");
    await popoutWindow.popoutContains("img");
    await popoutWindow.popoutClick(".o_move_previous");
    await popoutWindow.popoutContains("iframe");
    popoutWindow.close();
    await contains(".o_attachment_preview:not(.d-none)");
    expect(".o_attachment_preview").toBeVisible();
    await click(".o_attachment_preview .o_move_next");
    await contains(".o_attachment_preview img");
    await click(".o_attachment_preview .o_move_previous");
    await contains(".o_attachment_preview iframe");
    await click(".o_attachment_preview .o_attachment_control");
    await animationFrame();
    expect(".o_attachment_preview").not.toBeVisible();
});
