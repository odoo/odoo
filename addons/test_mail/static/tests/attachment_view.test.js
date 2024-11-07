import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { beforeEach, describe, test, expect } from "@odoo/hoot";
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

let popoutIframe, popoutWindow;

beforeEach(() => {
    popoutIframe = document.createElement("iframe");
    popoutWindow = {
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
        close: () => {
            popoutWindow.closed = true;
            popoutIframe.remove(popoutAttachmentViewBody());
        },
    };
});

patchWithCleanup(browser, {
    open: () => {
        popoutWindow.closed = false;
        queryOne(".o_popout_holder").append(popoutIframe);
        return popoutWindow;
    },
});

function popoutAttachmentViewBody() {
    return popoutWindow.document.querySelector(".o-mail-PopoutAttachmentView");
}
async function popoutIsEmpty() {
    await animationFrame();
    expect(popoutAttachmentViewBody()).toBe(null);
}
async function popoutContains(selector) {
    await animationFrame();
    await waitUntil(() => popoutAttachmentViewBody());
    const target = popoutAttachmentViewBody().querySelector(selector);
    expect(target).toBeDisplayed();
    return target;
}
async function popoutClick(selector) {
    const target = await popoutContains(selector);
    click(target);
}

test("Attachment view popout controls test", async () => {
    /*
     * This test makes sure that the attachment view controls are working in the following cases:
     * - Inside the popout window
     * - After closing the popout window
     */
    const pyEnv = await startServer();
    const recordId = pyEnv["mail.test.simple.main.attachment"].create({
        display_name: "first partner",
        message_attachment_count: 2,
    });
    pyEnv["ir.attachment"].create([
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
    await click(".o_attachment_preview .o_attachment_control");
    await animationFrame();
    expect(".o_attachment_preview").not.toBeVisible();
    await popoutClick(".o_move_next");
    await popoutContains("img");
    await popoutClick(".o_move_previous");
    await popoutContains("iframe");
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

test("Attachment view / chatter popout across multiple records test", async () => {
    const pyEnv = await startServer();
    const recordIds = pyEnv["mail.test.simple.main.attachment"].create([
        {
            display_name: "first partner",
            message_attachment_count: 1,
        },
        {
            display_name: "second partner",
            message_attachment_count: 0,
        },
        {
            display_name: "third partner",
            message_attachment_count: 1,
        },
    ]);
    pyEnv["ir.attachment"].create([
        {
            mimetype: "image/jpeg",
            res_id: recordIds[0],
            res_model: "mail.test.simple.main.attachment",
        },
        {
            mimetype: "application/pdf",
            res_id: recordIds[2],
            res_model: "mail.test.simple.main.attachment",
        },
    ]);
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

    async function navigateRecords() {
        /**
         * It should be called on the first record of recordIds
         * The popout window should be open
         * It navigates recordIds as 0 -> 1 -> 2 -> 0 -> 2
         */
        await animationFrame();
        expect(".o_attachment_preview").not.toBeVisible();
        await popoutContains("img");
        await click(".o_pager_next");
        await popoutIsEmpty();
        await click(".o_pager_next");
        await popoutContains("iframe");
        await click(".o_pager_next");
        await popoutContains("img");
        await click(".o_pager_previous");
        await popoutContains("iframe");
        popoutWindow.close();
        await contains(".o_attachment_preview:not(.d-none)");
    }

    patchUiSize({ size: SIZES.XXL });
    await start();
    await openFormView("mail.test.simple.main.attachment", recordIds[0], {
        resIds: recordIds,
    });
    await click(".o_attachment_preview .o_attachment_control");
    await navigateRecords();
    await openFormView("mail.test.simple.main.attachment", recordIds[0], {
        resIds: recordIds,
    });
    await click("button i[title='Pop out Attachments']");
    await navigateRecords();
});
