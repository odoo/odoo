/** @odoo-module **/

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    isScrolledToBottom,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { dom } from "web.test_utils";

const { triggerEvent } = dom;

QUnit.module("mail", {}, function () {
    QUnit.module("widgets", {}, function () {
        QUnit.module("form_renderer_tests.js");

        QUnit.skipRefactoring("chatter updating", async function (assert) {
            assert.expect(1);

            const pyEnv = await startServer();
            const [resPartnerId1, resPartnerId2] = pyEnv["res.partner"].create([
                { display_name: "first partner" },
                { display_name: "second partner" },
            ]);
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "res.partner",
                res_id: resPartnerId2,
            });
            const views = {
                "res.partner,false,form": `<form string="Partners">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                    <div class="oe_chatter">
                        <field name="message_ids"/>
                    </div>
                </form>`,
            };
            const { afterEvent, openFormView } = await start({
                serverData: { views },
            });
            await openFormView("res.partner", resPartnerId1, {
                props: {
                    resIds: [resPartnerId1, resPartnerId2],
                },
            });
            await afterNextRender(() =>
                afterEvent({
                    eventName: "o-thread-view-hint-processed",
                    func: () => document.querySelector(".o_pager_next").click(),
                    message:
                        "should wait until partner 12 thread loaded messages after clicking on next",
                    predicate: ({ hint, threadViewer }) => {
                        return (
                            hint.type === "messages-loaded" &&
                            threadViewer.thread.model === "res.partner" &&
                            threadViewer.thread.id === resPartnerId2
                        );
                    },
                })
            );
            assert.containsOnce(
                document.body,
                ".o-mail-message",
                "there should be a message in partner 12 thread"
            );
        });

        QUnit.skipRefactoring("post message on draft record", async function (assert) {
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
            const { click, insertText, openView } = await start({ serverData: { views } });
            await openView({
                res_model: "res.partner",
                views: [[false, "form"]],
            });
            await click(".o_ChatterTopbar_buttonSendMessage");
            await insertText(".o_ComposerTextInputView_textarea", "Test");
            await click(".o_ComposerView_buttonSend");
            assert.containsOnce(document.body, ".o_MessageView");
            assert.strictEqual(
                document.querySelector(".o_MessageView_prettyBody").textContent,
                "Test"
            );
        });

        QUnit.skipRefactoring(
            "schedule activities on draft record should prompt with scheduling an activity (proceed with action)",
            async function (assert) {
                const views = {
                    "res.partner,false,form": `<form string="Partners">
                        <sheet>
                            <field name="name"/>
                        </sheet>
                        <div class="oe_chatter">
                            <field name="activity_ids"/>
                        </div>
                    </form>`,
                };
                const { click, openView } = await start({ serverData: { views } });
                await openView({ res_model: "res.partner", views: [[false, "form"]] });
                await click(".o_ChatterTopbar_buttonScheduleActivity");
                assert.containsOnce(document.body, ".o_dialog:contains(Schedule Activity)");
            }
        );

        QUnit.skipRefactoring(
            "read more/less links are not duplicated when switching from read to edit mode",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({});
                const mailMessageId1 = pyEnv["mail.message"].create({
                    author_id: resPartnerId1,
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
                    res_id: resPartnerId1,
                });
                const views = {
                    "res.partner,false,form": `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
                };
                const { afterEvent, openView } = await start({
                    serverData: { views },
                });
                const openViewAction = {
                    res_model: "res.partner",
                    res_id: resPartnerId1,
                    views: [[false, "form"]],
                };
                await afterEvent({
                    func: () => openView(openViewAction),
                    eventName: "o-component-message-read-more-less-inserted",
                    message: "should wait until read more/less is inserted initially",
                    predicate: ({ message }) => message.id === mailMessageId1,
                });
                assert.containsOnce(document.body, ".o-mail-chatter", "there should be a chatter");
                assert.containsOnce(document.body, ".o-mail-message", "there should be a message");
                assert.containsOnce(
                    document.body,
                    ".o_MessageView_readMoreLess",
                    "there should be only one read more"
                );
            }
        );

        QUnit.skipRefactoring(
            "read more links becomes read less after being clicked",
            async function (assert) {
                assert.expect(5);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({});
                const mailMessageId1 = pyEnv["mail.message"].create([
                    {
                        author_id: resPartnerId1,
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
                        res_id: resPartnerId1,
                    },
                ]);
                const views = {
                    "res.partner,false,form": `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
                };
                const { afterEvent, openView } = await start({
                    serverData: { views },
                });
                const openViewAction = {
                    res_model: "res.partner",
                    res_id: resPartnerId1,
                    views: [[false, "form"]],
                };
                await afterEvent({
                    func: () => openView(openViewAction),
                    eventName: "o-component-message-read-more-less-inserted",
                    message: "should wait until read more/less is inserted initially",
                    predicate: ({ message }) => message.id === mailMessageId1,
                });
                assert.containsOnce(document.body, ".o-mail-chatter", "there should be a chatter");
                assert.containsOnce(document.body, ".o-mail-message", "there should be a message");
                assert.containsOnce(
                    document.body,
                    ".o_MessageView_readMoreLess",
                    "there should be a read more"
                );
                assert.strictEqual(
                    document.querySelector(".o_MessageView_readMoreLess").textContent,
                    "Read More",
                    "Read More/Less link should contain 'Read More' as text"
                );

                document.querySelector(".o_MessageView_readMoreLess").click();
                assert.strictEqual(
                    document.querySelector(".o_MessageView_readMoreLess").textContent,
                    "Read Less",
                    "Read Less/Less link should contain 'Read Less' as text after it has been clicked"
                );
            }
        );

        QUnit.skipRefactoring(
            "Form view not scrolled when switching record",
            async function (assert) {
                assert.expect(6);

                const pyEnv = await startServer();
                const [resPartnerId1, resPartnerId2] = pyEnv["res.partner"].create([
                    {
                        description: [...Array(60).keys()].join("\n"),
                        display_name: "Partner 1",
                    },
                    {
                        display_name: "Partner 2",
                    },
                ]);

                const messages = [...Array(60).keys()].map((id) => {
                    return {
                        model: "res.partner",
                        res_id: id % 2 ? resPartnerId1 : resPartnerId2,
                    };
                });
                pyEnv["mail.message"].create(messages);
                const views = {
                    "res.partner,false,form": `<form string="Partners">
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
                const { click, openView } = await start({
                    serverData: { views },
                });
                await openView(
                    {
                        res_model: "res.partner",
                        res_id: resPartnerId1,
                        views: [[false, "form"]],
                    },
                    {
                        resIds: [resPartnerId1, resPartnerId2],
                    }
                );

                const controllerContentEl = document.querySelector(".o_content");

                assert.strictEqual(
                    document.querySelector(".breadcrumb-item.active").textContent,
                    "Partner 1",
                    "Form view should display partner 'Partner 1'"
                );
                assert.strictEqual(
                    controllerContentEl.scrollTop,
                    0,
                    "The top of the form view is visible"
                );

                await afterNextRender(async () => {
                    controllerContentEl.scrollTop =
                        controllerContentEl.scrollHeight - controllerContentEl.clientHeight;
                    await triggerEvent(document.querySelector(".o-mail-thread"), "scroll");
                });
                assert.ok(
                    isScrolledToBottom(controllerContentEl),
                    "The controller container should be scrolled to its bottom"
                );

                await click(".o_pager_next");
                assert.strictEqual(
                    document.querySelector(".breadcrumb-item.active").textContent,
                    "Partner 2",
                    "The form view should display partner 'Partner 2'"
                );
                assert.strictEqual(
                    controllerContentEl.scrollTop,
                    0,
                    "The top of the form view should be visible when switching record from pager"
                );

                await click(".o_pager_previous");
                assert.strictEqual(
                    controllerContentEl.scrollTop,
                    0,
                    "Form view's scroll position should have been reset when switching back to first record"
                );
            }
        );

        QUnit.skipRefactoring(
            "Attachments that have been unlinked from server should be visually unlinked from record",
            async function (assert) {
                // Attachments that have been fetched from a record at certain time and then
                // removed from the server should be reflected on the UI when the current
                // partner accesses this record again.
                assert.expect(2);

                const pyEnv = await startServer();
                const [resPartnerId1, resPartnerId2] = pyEnv["res.partner"].create([
                    { display_name: "Partner1" },
                    { display_name: "Partner2" },
                ]);
                const [irAttachmentId1] = pyEnv["ir.attachment"].create([
                    {
                        mimetype: "text.txt",
                        res_id: resPartnerId1,
                        res_model: "res.partner",
                    },
                    {
                        mimetype: "text.txt",
                        res_id: resPartnerId1,
                        res_model: "res.partner",
                    },
                ]);
                const views = {
                    "res.partner,false,form": `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
                };
                const { click, openView } = await start({
                    serverData: { views },
                });
                await openView(
                    {
                        res_model: "res.partner",
                        res_id: resPartnerId1,
                        views: [[false, "form"]],
                    },
                    {
                        resId: resPartnerId1,
                        resIds: [resPartnerId1, resPartnerId2],
                    }
                );
                assert.strictEqual(
                    document.querySelector(".o_ChatterTopbar_buttonCount").textContent,
                    "2",
                    "Partner1 should have 2 attachments initially"
                );

                // The attachment links are updated on (re)load,
                // so using pager is a way to reload the record "Partner1".
                await click(".o_pager_next");
                // Simulate unlinking attachment 1 from Partner 1.
                pyEnv["ir.attachment"].write([irAttachmentId1], { res_id: 0 });
                await click(".o_pager_previous");
                assert.strictEqual(
                    document.querySelector(".o_ChatterTopbar_buttonCount").textContent,
                    "1",
                    "Partner1 should now have 1 attachment after it has been unlinked from server"
                );
            }
        );

        QUnit.skipRefactoring(
            "[TECHNICAL] unfolded read more/less links should not fold on message click besides those button links",
            async function (assert) {
                // message click triggers a re-render. Before writing of this test, the
                // insertion of read more/less links were done during render. This meant
                // any re-render would re-insert the read more/less links. If some button
                // links were unfolded, any re-render would fold them again.
                //
                // This previous behavior is undesirable, and results to bothersome UX
                // such as inability to copy/paste unfolded message content due to click
                // from text selection automatically folding all read more/less links.
                assert.expect(3);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({ display_name: "Someone" });
                pyEnv["mail.message"].create({
                    author_id: resPartnerId1,
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
                    res_id: resPartnerId1,
                });
                const views = {
                    "res.partner,false,form": `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
                };
                const { click, openView } = await start({
                    serverData: { views },
                });
                await openView({
                    res_model: "res.partner",
                    res_id: resPartnerId1,
                    views: [[false, "form"]],
                });
                assert.strictEqual(
                    document.querySelector(".o_MessageView_readMoreLess").textContent,
                    "Read More",
                    "Read More/Less link on message should be folded initially (Read More)"
                );

                document.querySelector(".o_MessageView_readMoreLess").click(),
                    assert.strictEqual(
                        document.querySelector(".o_MessageView_readMoreLess").textContent,
                        "Read Less",
                        "Read More/Less link on message should be unfolded after a click from initial rendering (read less)"
                    );

                await click(".o-mail-message");
                assert.strictEqual(
                    document.querySelector(".o_MessageView_readMoreLess").textContent,
                    "Read Less",
                    "Read More/Less link on message should still be unfolded after a click on message aside of this button click (Read Less)"
                );
            }
        );
    });
});
