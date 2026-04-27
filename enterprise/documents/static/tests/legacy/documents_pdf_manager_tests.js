/** @odoo-module **/

import { PdfManager } from "@documents/owl/components/pdf_manager/pdf_manager";
import { getFixture, nextTick, click, patchWithCleanup, mount } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { commandService } from "@web/core/commands/command_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { uiService } from "@web/core/ui/ui_service";
import { registry } from "@web/core/registry";
import testUtils from "@web/../tests/legacy_tests/helpers/test_utils";

const serviceRegistry = registry.category("services");

let env;
let target;

async function mountSetup(PdfManager, target, env) {
    await mount(PdfManager, target, {
        env,
        props: {
            documents: [
                { id: 1, name: "yop", mimetype: "application/pdf", available_embedded_actions_ids: [1, 2] },
                { id: 2, name: "blip", mimetype: "application/pdf", available_embedded_actions_ids: [1] },
            ],
            embeddedActions: [
                { id: 1, name: "action1"},
                { id: 2, name: "action2"},
            ],
            onProcessDocuments: async () => {},
            close: () => {},
        },
    });
}

QUnit.module("documents", {}, function () {
    QUnit.module(
        "documents_pdf_manager_tests.js",
        {
            async beforeEach() {
                patchWithCleanup(PdfManager.prototype, {
                    async _loadAssets() {},
                    async _getPdf() {
                        return {
                            getPage: (number) => ({ number }),
                            numPages: 6,
                        };
                    },
                    async _isBlankPage(page, canvas) {
                        return false;
                    },
                    async _renderCanvas(page, { width, height }) {
                        const canvas = document.createElement("canvas");
                        canvas.width = width;
                        canvas.height = height;
                        return canvas;
                    },
                });
                serviceRegistry.add("notification", notificationService);
                serviceRegistry.add("ui", uiService);
                serviceRegistry.add("dialog", dialogService);
                serviceRegistry.add("hotkey", hotkeyService);
                serviceRegistry.add("command", commandService);
                env = await makeTestEnv({ serviceRegistry });
                target = getFixture();
            },
        },
        () => {
            QUnit.test("Pdf Manager basic rendering", async function (assert) {
                assert.expect(10);

                await mountSetup(PdfManager, target, env);
                await nextTick();

                assert.containsOnce(
                    target,
                    ".o_documents_pdf_manager_top_bar",
                    "There should be one top bar"
                );
                assert.containsOnce(
                    target,
                    ".o_documents_pdf_page_viewer",
                    "There should be one page viewer"
                );
                assert.strictEqual(
                    target.querySelectorAll(".o_pdf_manager_button")[0].innerText,
                    "Split",
                    "There should be a split button"
                );
                assert.strictEqual(
                    target.querySelectorAll(".o_pdf_manager_button")[2].innerText,
                    "ADD FILE",
                    "There should be a ADD FILE button"
                );
                assert.strictEqual(
                    target.querySelectorAll(".o_pdf_manager_button")[3].innerText,
                    "ACTION1",
                    "There should be a ACTION1 button"
                );
                assert.strictEqual(
                    target.querySelectorAll(".o_pdf_manager_button")[4].innerText,
                    "ACTION2",
                    "There should be a ACTION2 button"
                );
                assert.containsOnce(
                    target,
                    ".o_pdf_separator_selected",
                    "There should be one active separator"
                );
                assert.containsN(target, ".o_pdf_page", 12, "There should be 12 pages");
                assert.containsN(
                    target,
                    ".o_documents_pdf_button_wrapper",
                    12,
                    "There should be 12 button wrappers"
                );
                assert.containsN(
                    target,
                    ".o_pdf_group_name_wrapper",
                    2,
                    "There should be 2 name plates"
                );
            });

            QUnit.test("Pdf Manager: page interactions", async function (assert) {
                assert.expect(4);

                await mountSetup(PdfManager, target, env);
                await nextTick();

                assert.containsOnce(
                    target,
                    ".o_pdf_separator_selected",
                    "There should be one active separator"
                );
                await click(target.querySelectorAll(".o_page_splitter_wrapper")[1]);
                assert.containsN(
                    target,
                    ".o_pdf_separator_selected",
                    2,
                    "There should be 2 active separator"
                );
                assert.containsN(
                    target,
                    ".o_pdf_page_selected",
                    12,
                    "There should be 12 selected pages"
                );
                await click(target.querySelectorAll(".o_documents_pdf_page_selector")[3]);
                assert.containsN(
                    target,
                    ".o_pdf_page_selected",
                    11,
                    "There should be 11 selected pages"
                );
            });

            QUnit.test("Pdf Manager: drag & drop", async function (assert) {
                assert.expect(5);

                await mountSetup(PdfManager, target, env);
                await nextTick();

                assert.containsN(
                    target,
                    ".o_pdf_separator_selected",
                    1,
                    "There should be one active separator"
                );
                assert.containsOnce(
                    target.querySelectorAll(".o_documents_pdf_page_frame")[6],
                    ".o_pdf_name_display",
                    "The seventh page should have a name plate"
                );
                const startEvent = new Event("dragstart", { bubbles: true });
                const dataTransfer = new DataTransfer();
                startEvent.dataTransfer = dataTransfer;
                target
                    .querySelectorAll(".o_documents_pdf_canvas_wrapper")[11]
                    .dispatchEvent(startEvent);
                const endEvent = new Event("drop", { bubbles: true });
                endEvent.dataTransfer = dataTransfer;
                target
                    .querySelectorAll(".o_documents_pdf_canvas_wrapper")[0]
                    .dispatchEvent(endEvent);
                await nextTick();
                assert.containsN(
                    target,
                    ".o_pdf_separator_selected",
                    1,
                    "There should be one active separator"
                );
                assert.containsNone(
                    target.querySelectorAll(".o_documents_pdf_page_frame")[6],
                    ".o_pdf_name_display",
                    "The seventh page shouldn't have a name plate"
                );
                assert.containsOnce(
                    target.querySelectorAll(".o_documents_pdf_page_frame")[7],
                    ".o_pdf_name_display",
                    "The eight page should have a name plate"
                );
            });

            QUnit.test("Pdf Manager: select/Unselect all pages", async function (assert) {
                assert.expect(3);

                await mountSetup(PdfManager, target, env);
                await nextTick();

                await click(target.querySelector(".o_documents_pdf_page_viewer"));
                assert.containsN(
                    target,
                    ".o_pdf_page_selected",
                    0,
                    "There should be no page selected"
                );
                await testUtils.dom.triggerEvent(window, "keydown", { key: "a", ctrlKey: true });
                assert.containsN(
                    target,
                    ".o_pdf_page_selected",
                    12,
                    "There should be 12 pages selected"
                );
                await testUtils.dom.triggerEvent(window, "keydown", { key: "a", ctrlKey: true });
                assert.containsN(
                    target,
                    ".o_pdf_page_selected",
                    0,
                    "There should be no page selected"
                );
            });

            QUnit.test(
                "Pdf Manager: select pages with mouse area selection",
                async function (assert) {
                    assert.expect(2);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    const viewer = document.querySelector(".o_documents_pdf_page_viewer");
                    const top = viewer.getBoundingClientRect().top;
                    const left = viewer.getBoundingClientRect().left;
                    const bottom = viewer.getBoundingClientRect().bottom;
                    const right = viewer.getBoundingClientRect().right;

                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "a",
                        ctrlKey: true,
                    });
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    const mouseDownEvent = new MouseEvent("mousedown", {
                        clientX: left,
                        clientY: top,
                    });
                    target.dispatchEvent(mouseDownEvent);
                    await nextTick();
                    const mouseMoveEvent = new MouseEvent("mousemove", {
                        clientX: right,
                        clientY: bottom,
                    });
                    // 2 test events are needed to trigger the changes in the DOM. Due to rerendering of state variables
                    target.dispatchEvent(mouseMoveEvent);
                    await nextTick();
                    target.dispatchEvent(mouseMoveEvent);
                    await nextTick();
                    const mouseUpEvent = new MouseEvent("mouseup", {
                        clientX: right,
                        clientY: bottom,
                    });
                    target.dispatchEvent(mouseUpEvent);
                    await nextTick();
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        12,
                        "There should be 12 pages selected"
                    );
                }
            );

            QUnit.test(
                "Pdf Manager: puts separators on active pages by pressing control+s",
                async function (assert) {
                    assert.expect(3);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    await click(target.querySelector(".o_documents_pdf_page_viewer"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "a",
                        ctrlKey: true,
                    });
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        12,
                        "There should be 12 pages selected"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", { key: "s", ctrlKey: true });
                    assert.containsN(
                        target,
                        ".o_pdf_separator_selected",
                        11,
                        "There should be 11 active separators"
                    );
                }
            );

            QUnit.test(
                "Pdf Manager: click on page bottom area selects the page",
                async function (assert) {
                    assert.expect(2);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    await click(target.querySelector(".o_documents_pdf_page_viewer"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    await click(target.querySelector(".o_bottom_selection"));
                    assert.containsOnce(
                        target,
                        ".o_pdf_page_selected",
                        "There should be one page selected"
                    );
                }
            );

            QUnit.test(
                "Pdf Manager: click on page selector selects the page",
                async function (assert) {
                    assert.expect(2);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    await click(target.querySelector(".o_documents_pdf_page_viewer"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    await click(target.querySelector(".o_documents_pdf_page_selector"));
                    assert.containsOnce(
                        target,
                        ".o_pdf_page_selected",
                        "There should be one page selected"
                    );
                }
            );

            QUnit.test("Pdf Manager: arrow navigation", async function (assert) {
                assert.expect(3);

                await mountSetup(PdfManager, target, env);
                await nextTick();

                await click(target.querySelector(".o_documents_pdf_page_viewer"));
                assert.containsN(
                    target,
                    ".o_pdf_page_selected",
                    0,
                    "There should be no page selected"
                );
                await testUtils.dom.triggerEvent(window, "keydown", { key: "arrowRight" });
                assert.containsOnce(
                    target.querySelectorAll(".o_documents_pdf_page_frame")[0],
                    ".o_pdf_page_focused",
                    "The first page should be focused"
                );
                await testUtils.dom.triggerEvent(window, "keydown", { key: "arrowRight" });
                assert.containsOnce(
                    target.querySelectorAll(".o_documents_pdf_page_frame")[1],
                    ".o_pdf_page_focused",
                    "The second page should be focused"
                );
            });

            QUnit.test(
                "Pdf Manager: arrow navigation + shift page activation",
                async function (assert) {
                    assert.expect(7);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    await click(target.querySelector(".o_documents_pdf_page_viewer"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "arrowRight",
                        shiftKey: true,
                    });
                    assert.containsOnce(
                        target.querySelectorAll(".o_documents_pdf_page_frame")[0],
                        ".o_pdf_page_focused",
                        "The first page should be focused"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "arrowRight",
                        shiftKey: true,
                    });
                    assert.containsOnce(
                        target.querySelectorAll(".o_documents_pdf_page_frame")[1],
                        ".o_pdf_page_focused",
                        "The second page should be focused"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "arrowRight",
                        shiftKey: true,
                    });
                    assert.containsOnce(
                        target.querySelectorAll(".o_documents_pdf_page_frame")[2],
                        ".o_pdf_page_focused",
                        "The third page should be focused"
                    );
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        3,
                        "3 pages should be selected"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "arrowLeft",
                        shiftKey: true,
                    });
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "arrowLeft",
                        shiftKey: true,
                    });
                    assert.containsOnce(
                        target.querySelectorAll(".o_documents_pdf_page_frame")[0],
                        ".o_pdf_page_focused",
                        "The first page should be focused"
                    );
                    assert.containsOnce(
                        target,
                        ".o_pdf_page_selected",
                        "One page should be selected"
                    );
                }
            );

            QUnit.test(
                "Pdf Manager: ctrl+shift+arrow shortcut multiple activation",
                async function (assert) {
                    assert.expect(2);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    await click(target.querySelector(".o_documents_pdf_page_viewer"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", { key: "arrowRight" });
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "arrowRight",
                        shiftKey: true,
                        ctrlKey: true,
                    });
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        6,
                        "There should be 6 pages selected"
                    );
                }
            );

            QUnit.test(
                "Pdf Manager: ctrl+arrow shortcut navigation between groups",
                async function (assert) {
                    assert.expect(2);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    await click(target.querySelector(".o_documents_pdf_page_viewer"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    await testUtils.dom.triggerEvent(window, "keydown", { key: "arrowRight" });
                    await testUtils.dom.triggerEvent(window, "keydown", {
                        key: "arrowRight",
                        ctrlKey: true,
                    });
                    assert.containsOnce(
                        target.querySelectorAll(".o_documents_pdf_page_frame")[6],
                        ".o_pdf_page_focused",
                        "The seventh page should be focused"
                    );
                }
            );

            QUnit.test(
                "Pdf Manager: click on group name should select all the group",
                async function (assert) {
                    assert.expect(2);

                    await mountSetup(PdfManager, target, env);
                    await nextTick();

                    await click(target.querySelector(".o_documents_pdf_page_viewer"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        0,
                        "There should be no page selected"
                    );
                    await click(target.querySelector(".o_pdf_name_display"));
                    assert.containsN(
                        target,
                        ".o_pdf_page_selected",
                        6,
                        "6 pages should be selected"
                    );
                }
            );

            QUnit.test("Pdf Manager: page preview behaviour", async function (assert) {
                assert.expect(7);

                await mountSetup(PdfManager, target, env);
                await nextTick();

                await click(target.querySelector(".o_documents_pdf_page_viewer"));
                assert.containsN(
                    target,
                    ".o_pdf_page_selected",
                    0,
                    "There should be no page selected"
                );
                await click(target.querySelector(".o_documents_pdf_canvas_wrapper"));
                assert.containsOnce(target, ".o_pdf_page_preview", "The previewer should be open");
                assert.strictEqual(
                    target.querySelector(".o_page_index").textContent,
                    "1/12",
                    "Index of the first page should be displayed"
                );
                assert.strictEqual(
                    target.querySelector(".o_page_index").textContent,
                    "1/12",
                    "Index of the first page should be displayed"
                );
                assert.strictEqual(
                    target.querySelector(".o_page_name").textContent,
                    "yop-p1",
                    "Name of the group should be displayed"
                );
                await testUtils.dom.triggerEvent(window, "keydown", { key: "arrowRight" });
                assert.strictEqual(
                    target.querySelector(".o_page_index").textContent,
                    "2/12",
                    "Index of the second page should be displayed"
                );
                assert.strictEqual(
                    target.querySelector(".o_page_name").textContent,
                    "yop-p2",
                    "Name of the group should be displayed"
                );
            });
        }
    );
});
