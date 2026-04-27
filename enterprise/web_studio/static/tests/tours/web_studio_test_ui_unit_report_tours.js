/** @odoo-module */
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { patch } from "@web/core/utils/patch";
import { parseXML, serializeXML } from "@web/core/utils/xml";
import { assertEqual, stepNotInStudio, nextTick } from "@web_studio/../tests/tours/tour_helpers";
import { cookie } from "@web/core/browser/cookie";
import { Editor } from "@html_editor/editor";
import { nodeSize } from "@html_editor/utils/position";
import { waitUntil } from "@odoo/hoot-dom";

const getBoundingClientRect = Element.prototype.getBoundingClientRect;

const editorsWeakMap = new WeakMap();
patch(Editor.prototype, {
    attachTo(editable) {
        editorsWeakMap.set(editable.ownerDocument, this);
        return super.attachTo(...arguments);
    },
});

function normalizeXML(str) {
    const doc = parseXML(str);
    /* Recursively trim text nodes conditionally
     * if they start or end with a newline (\n).
     * In that case we make the assumption that all whitespaces
     * are materializing indentation.
     * If there are only spaces (\s), we make the assumption that they
     * are actual spaces that are visible to the naked eye of the user.
     */
    const nodes = [...doc.childNodes];
    for (const node of nodes) {
        if (node.nodeType === Node.TEXT_NODE) {
            let nodeValue = node.nodeValue;
            if (nodeValue.startsWith("\n")) {
                nodeValue = nodeValue.trimStart();
            }
            if (nodeValue.endsWith("\n")) {
                nodeValue = nodeValue.trimEnd();
            }
            node.nodeValue = nodeValue;
        }
        if (node.nodeType === Node.ELEMENT_NODE) {
            nodes.push(...node.childNodes);
        }
    }

    return serializeXML(doc);
}

function insertText(element, text, offsets = null) {
    const doc = element.ownerDocument;
    const sel = doc.getSelection();
    let range;
    if (sel && sel.rangeCount) {
        range = sel.getRangeAt(sel.rangeCount - 1);
    }
    if (offsets || !range) {
        const { start, end } = offsets || {};
        sel.removeAllRanges();
        range = doc.createRange();
        range.setStart(element, start || 0);
        range.setEnd(element, end || start || 0);
        sel.addRange(range);
    }

    const evOptions = {
        view: doc.defaultView,
        bubbles: true,
        composed: true,
        cancelable: true,
        isTrusted: true,
    };

    for (const char of text) {
        element.dispatchEvent(
            new KeyboardEvent("keydown", {
                ...evOptions,
                key: char,
            })
        );
        element.dispatchEvent(
            new KeyboardEvent("keypress", {
                ...evOptions,
                key: char,
            })
        );
        element.dispatchEvent(
            new InputEvent("input", {
                ...evOptions,
                inputType: "insertText",
                data: char,
            })
        );
        const newNode = doc.createTextNode(char);
        element.append(newNode);
        range.setEndAfter(newNode);

        element.dispatchEvent(
            new KeyboardEvent("keyup", {
                ...evOptions,
                key: char,
            })
        );
    }
}

function openEditorPowerBox(element, offsets = null) {
    return insertText(element, "/", offsets);
}

/* global ace */

// This function allows to use and test the feature that automatically
// saves when we leave the reportEditor.
// Implem detail: it is done at willUnmount, so we need to wait for the promise
// to be sure we leave the tour when the save is done.
function patchReportEditorModelForSilentSave() {
    const saveProms = [];
    const { ReportEditorModel } = odoo.loader.modules.get(
        "@web_studio/client_action/report_editor/report_editor_model"
    );
    const _unpatch = patch(ReportEditorModel.prototype, {
        saveReport() {
            const prom = super.saveReport(...arguments);
            saveProms.push(prom);
            return prom;
        },
    });

    return {
        wait: async (unpatch = true) => {
            await Promise.all(saveProms);
            if (unpatch) {
                _unpatch();
            }
        },
        saveProms,
        unpatch: _unpatch,
    };
}

registry
    .category("web_tour.tours")
    .add("web_studio.test_disable_fields_commands_when_unavailable", {
        steps: () => [
            {
                trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p",
                async run(helpers) {
                    const el = this.anchor;
                    openEditorPowerBox(el);
                },
            },
            {
                trigger: ".o-we-powerbox .o-we-command-name",
                run: (target) => {
                    const commands = Array.from(
                        document.querySelectorAll(".o-we-command-name")
                    ).map((e) => e.textContent);

                    if (commands.includes("Field") || commands.includes("Dynamic Table")) {
                        throw new Error(
                            "`Field`|`Dynamic Table` shouldn't be present when we don't have a record"
                        );
                    }
                },
            },
        ],
    });

let silentPatch;
registry.category("web_tour.tours").add("web_studio.test_basic_report_edition", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar input[id='name']",
            run: "edit modified in test && click body",
        },
        {
            trigger: ".o_web_studio_menu .breadcrumb-item.active",
            run() {
                assertEqual(this.anchor.textContent, "modified in test");
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run: "editor edited with odoo editor",
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            run: "editor edited with odoo editor 2",
        },
        {
            // Don't explicitly save, this is a feature
            trigger: ".o_web_studio_leave a",
            run(helpers) {
                silentPatch = patchReportEditorModelForSilentSave();
                helpers.click();
            },
        },
        ...stepNotInStudio(),
        {
            trigger: "body",
            run() {
                return silentPatch.wait();
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_basic_report_edition_xml", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_xml_resource_selector .o_web_studio_xml_resource_select_menu",
            run() {
                assertEqual(
                    this.anchor.textContent,
                    "web_studio.test_report_document (web_studio.test_report_document)"
                );
            },
        },
        {
            trigger: ".o_web_studio_code_editor.ace_editor",
            run() {
                ace.edit(this.anchor)
                    .getSession()
                    .insert(
                        { row: 2, column: 0 },
                        '<span class="test-added-0">in document view</span>\n'
                    );
            },
        },
        {
            trigger: ".o_web_studio_xml_resource_selector .o_select_menu_toggler",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu",
            run(helpers) {
                const mainView = Array.from(
                    this.anchor.querySelectorAll(".o_select_menu_item")
                ).find(
                    (el) =>
                        el.textContent ===
                        "web_studio.test_report (web_studio.studio_test_report_view)"
                );
                helpers.click(mainView);
            },
        },
        {
            trigger: ".o_web_studio_code_editor.ace_editor",
            run() {
                ace.edit(this.anchor)
                    .getSession()
                    .insert(
                        { row: 2, column: 0 },
                        '<span class="test-added-1">in main view</span>\n'
                    );
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
        {
            trigger: ".o-web-studio-report-container :iframe body",
            run() {
                assertEqual(
                    this.anchor.querySelector(".test-added-0").textContent,
                    "in document view"
                );
                assertEqual(this.anchor.querySelector(".test-added-1").textContent, "in main view");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_basic_report_edition_discard", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar input[id='name']",
            run: "edit modified in test && click body",
        },
        {
            trigger: ".o_web_studio_menu .breadcrumb-item.active",
            run() {
                assertEqual(this.anchor.textContent, "modified in test");
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run: "editor edited with odoo editor",
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            run: "editor edited with odoo editor 2",
        },
        {
            trigger: ".o-web-studio-discard-report.btn-secondary",
            run: "click",
        },
        {
            trigger: ".modal-dialog .btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run() {
                assertEqual(this.anchor.textContent, "");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_basic_report_edition_cancel_discard", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar input[id='name']",
            run: "edit modified in test && click body",
        },
        {
            trigger: ".o_web_studio_menu .breadcrumb-item.active",
            run() {
                assertEqual(this.anchor.textContent, "modified in test");
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run: "editor edited with odoo editor",
        },
        {
            trigger: ".o-web-studio-discard-report.btn-secondary",
            run: "click",
        },
        {
            trigger: ".modal-dialog .btn-secondary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run() {
                assertEqual(this.anchor.textContent, "edited with odoo editor");
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_basic_report_edition_xml_discard", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_code_editor.ace_editor",
            run() {
                ace.edit(this.anchor)
                    .getSession()
                    .insert({ row: 2, column: 0 }, '<span class="test-added">in main view</span>');
            },
        },
        {
            trigger: ".o-web-studio-discard-report.btn-secondary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-report-container :iframe body",
            run() {
                const element = this.anchor.querySelector(".test-added");
                if (element) {
                    throw new Error("The changes should have been discarded");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_basic_report_edition_error", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run: "editor edited with odoo editor",
        },
        {
            // Brutally add a t-else: this will crash in python on save
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable",
            run() {
                const editor = editorsWeakMap.get(this.anchor.ownerDocument);
                const telse = editor.document.createElement("t");
                telse.setAttribute("t-else", "");
                editor.shared.dom.insert(telse);
                editor.shared.history.addStep();
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            run: "editor edited with odoo editor 2",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_notification .o_notification_title",
            run() {
                assertEqual(this.anchor.textContent, "Report edition failed");
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run() {
                // The iframe shouldn't have been reset after an error
                assertEqual(this.anchor.textContent, "edited with odoo editor");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_basic_report_edition_xml_error", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_code_editor.ace_editor",
            run() {
                ace.edit(this.anchor)
                    .getSession()
                    .insert(
                        { row: 2, column: 0 },
                        '<span t-else="" class="test-added">in main view</span>'
                    );
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_notification .o_notification_title",
            run() {
                assertEqual(this.anchor.textContent, "Report edition failed");
            },
        },
        {
            trigger: ".o-web-studio-report-container :iframe body",
            run() {
                const element = this.anchor.querySelector(".test-added");
                if (element) {
                    throw new Error("The changes should have been discarded");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_report_reset_archs", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar button[name='report_reset_archs']",
            run: "click",
        },
        {
            trigger: ".modal-footer",
            run(helpers) {
                const button = Array.from(this.anchor.querySelectorAll("button")).find(
                    (el) => el.textContent === "Reset report" && el.classList.contains("btn-danger")
                );
                helpers.click(button);
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(1)",
            run() {
                assertEqual(this.anchor.textContent, "from file");
            },
        },
    ],
});

let downloadProm;
const steps = [];
registry.category("web_tour.tours").add("web_studio.test_print_preview", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar button[name='report_print_preview']",
            run(helpers) {
                downloadProm = new Promise((resolve) => {
                    const unpatch = patch(download, {
                        _download(options) {
                            steps.push("download report");
                            const context = JSON.parse(options.data.context);
                            assertEqual(context["report_pdf_no_attachment"], true);
                            assertEqual(context["discard_logo_check"], true);
                            assertEqual(context["active_ids"].length, 1);
                            unpatch();
                            resolve();
                        },
                    });
                });
                return helpers.click();
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg",
            async run() {
                await downloadProm;
                assertEqual(steps.length, 1);
                assertEqual(steps[0], "download report");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_table_rendering", {
    steps: () => [
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable .valid_table",
            run() {
                assertEqual(
                    this.anchor.outerHTML.replace(/\n\s*/g, ""),
                    `<table class="valid_table" o-diff-key="3">
                        <tbody o-diff-key="4"><tr o-diff-key="5"><td o-diff-key="6">I am valid</td></tr>
                    </tbody></table>`.replace(/\n\s*/g, "")
                );
            },
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable .invalid_table",
            run() {
                assertEqual(
                    this.anchor.outerHTML.replace(/\n\s*/g, ""),
                    `<q-table class="invalid_table oe_unbreakable" o-diff-key="7" style="--q-table-col-count: 1;">
                    <t t-foreach="doc.child_ids" t-as="child" o-diff-key="8" oe-context="{&quot;docs&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: false}, &quot;company&quot;: {&quot;model&quot;: &quot;res.company&quot;, &quot;name&quot;: &quot;Companies&quot;, &quot;in_foreach&quot;: false}, &quot;doc&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: true}, &quot;child&quot;: {&quot;model&quot;: &quot;res.partner&quot;, &quot;name&quot;: &quot;Contact&quot;, &quot;in_foreach&quot;: true}}">
                        <q-tr o-diff-key="9" class="oe_unbreakable"><q-td o-diff-key="10" class="oe_unbreakable">I am not valid</q-td></q-tr>
                    </t>
                </q-table>`.replace(/\n\s*/g, "")
                );
            },
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable .invalid_table q-td",
            run: "editor edited with odooEditor",
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(1)",
            run: "editor p edited with odooEditor",
        },
        {
            trigger: ".o_web_studio_sidebar input[id='name']",
            run: "edit modified && click body",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_field_placeholder", {
    steps: () => [
        {
            // 1 sec delay to make sure we call the download route
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            async run(helpers) {
                const el = this.anchor;
                openEditorPowerBox(el);
            },
        },
        {
            trigger: ".o-we-powerbox .o-we-command-description:contains(Insert a field)",
            run: "click",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder",
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg div:has(> .o-web-studio-report-container)",
            async run() {
                const placeholderBox = getBoundingClientRect.call(
                    document.querySelector(".o-web-studio-field-dynamic-placeholder")
                );
                assertEqual(this.anchor.scrollTop, 0);
                this.anchor.scrollTop = 9999;
                await waitUntil(() => {
                    const newPlaceholderbox = getBoundingClientRect.call(
                        document.querySelector(".o-web-studio-field-dynamic-placeholder")
                    );
                    // The field placeholder should have followed its anchor, and it happens that the anchor's container
                    // has been scrolled, so the anchor has moved upwards (and is actually outside of the viewPort, to the top)
                    return placeholderBox.top > newPlaceholderbox.top;
                });
            },
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit Job Position",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_item_name:contains(Job Position)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_default_value_input input",
            run: "edit some default value",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover",
            run: "press Enter",
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable span[t-field='doc.function'][title='doc.function']",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(0)",
            run() {
                insertText(this.anchor, "edited with odooEditor");
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_add_field_blank_report", {
    steps: () => [
        {
            // edit reports
            trigger: ".o_web_studio_menu li a:contains(Reports)",
            run: "click",
        },
        {
            // create a new report
            trigger: ".o_control_panel .o-kanban-button-new",
            run: "click",
        },
        {
            // select basic layout
            trigger: '.o_web_studio_report_layout_dialog div[data-layout="web.basic_layout"]',
            run: "click",
        },
        {
            trigger: ":iframe .odoo-editor-editable .page div",
            async run(helpers) {
                const el = this.anchor;
                openEditorPowerBox(el);
            },
        },
        {
            trigger: ".o-we-powerbox .o-we-command-description:contains(Insert a field)",
            run: "click",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder",
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg div:has(> .o-web-studio-report-container)",
            async run() {
                const placeholderBox = getBoundingClientRect.call(
                    document.querySelector(".o-web-studio-field-dynamic-placeholder")
                );
                assertEqual(this.anchor.scrollTop, 0);
                this.anchor.scrollTop = 9999;
                await waitUntil(() => {
                    const newPlaceholderbox = getBoundingClientRect.call(
                        document.querySelector(".o-web-studio-field-dynamic-placeholder")
                    );
                    // The field placeholder should have followed its anchor, and it happens that the anchor's container
                    // has been scrolled, so the anchor has moved upwards (and is actually outside of the viewPort, to the top)
                    return placeholderBox.top > newPlaceholderbox.top;
                });
            },
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit Job Position",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_item_name:contains(Job Position)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_default_value_input input",
            run: "edit some default value",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover",
            run: "press Enter",
        },
        {
            // check that field was added successfully
            trigger: ":iframe .odoo-editor-editable .page div > span:contains(some default value)",
        },
        {
            trigger: ":iframe .odoo-editor-editable .page div",
            run() {
                insertText(this.anchor, "Custo");
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_toolbar_appearance", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable .to_edit",
            run() {
                const anchor = this.anchor;
                const doc = anchor.ownerDocument;
                const selection = doc.getSelection();
                selection.removeAllRanges();
                const range = doc.createRange();
                range.selectNode(anchor.firstChild);
                selection.addRange(range);
            },
        },
        {
            trigger: ".o-we-toolbar",
        },
        {
            trigger: ".o-we-toolbar button[name='bold']",
            run: "click",
        },
        {
            trigger: ".o-we-toolbar button[name='italic']",
            run: "click",
        },
        {
            trigger: ".o-web-studio-discard-report",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o-we-toolbar))",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_edition_without_lang", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(1)",
            run() {
                assertEqual(this.anchor.textContent, "original term");
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(1)",
            async run() {
                insertText(this.anchor, " edited");
            },
        },
        {
            trigger: ".o_web_studio_sidebar button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_xml_resource_select_menu button.o_select_menu_toggler",
            run: "click",
        },
        {
            trigger:
                ".o-dropdown--menu .o_select_menu_item_label:contains(report_editor_customization_diff)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_code_editor_info .o_field_translate",
            run: "click",
        },
        {
            trigger: ".o_translation_dialog .row:eq(1)",
            run() {
                assertEqual(this.anchor.children[0].textContent.trim(), "French / Français");
                assertEqual(this.anchor.children[1].textContent.trim(), "original term edited");
            },
        },
        {
            trigger: ".o_translation_dialog .row:eq(1) textarea",
            run: "edit translated edited term && click body",
        },
        {
            trigger: ".modal-footer button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editor",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_report_xml_other_record", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_xml_editor",
        },
        {
            trigger: ".o-web-studio-report-container :iframe body p:contains(partner_1)",
        },
        {
            trigger: ".o-web-studio-report-search-record input:value(partner_1)",
        },
        {
            trigger: ".o-web-studio-report-pager .o_pager_next",
            run: "click",
        },
        {
            trigger: ".o-web-studio-report-container :iframe body p:contains(partner_2)",
        },
        {
            trigger: ".o-web-studio-report-search-record input:value(partner_2)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_partial_eval", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-container :iframe .odoo-editor-editable .lol",
            run() {
                const closestContextElement = this.anchor.closest("[oe-context]");
                const oeContext = closestContextElement.getAttribute("oe-context");
                const expected = {
                    docs: { model: "res.partner", name: "Contact", in_foreach: false },
                    company: { model: "res.company", name: "Companies", in_foreach: false },
                    doc: { model: "res.partner", name: "Contact", in_foreach: true },
                    my_children: { model: "res.partner", name: "Contact", in_foreach: false },
                    child: { model: "res.partner", name: "Contact", in_foreach: true },
                };
                assertEqual(JSON.stringify(JSON.parse(oeContext)), JSON.stringify(expected));
            },
        },
        {
            trigger: ".o-web-studio-report-container :iframe .odoo-editor-editable .couic",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_render_multicompany", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-container :iframe .odoo-editor-editable .test_layout",
        },
        {
            trigger: ".o-web-studio-report-container :iframe .odoo-editor-editable img",
            run() {
                const cids = cookie.get("cids").split("-");
                assertEqual(this.anchor.getAttribute("src"), `/logo.png?company=${cids[0]}`);
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_add_non_searchable_field", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            async run(helpers) {
                const el = this.anchor;
                openEditorPowerBox(el);
            },
        },
        {
            trigger: ".o-we-powerbox .o-we-command-description:contains(Insert a field)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit Avatar",
        },
        {
            trigger: "[data-name=avatar_1024] > button.o_model_field_selector_popover_item_name",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_default_value_input input",
            run: "edit file default value",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover",
            run: "press Enter",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_report_edition_binary_field", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            async run(helpers) {
                const el = this.anchor;
                openEditorPowerBox(el);
            },
        },
        {
            trigger: ".o-we-powerbox .o-we-command-description:contains(Insert a field)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit Company",
        },
        {
            trigger: "[data-name=company_id] > button.o_model_field_selector_popover_item_relation",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit New File",
        },
        {
            trigger:
                ".o_model_field_selector_popover_item_name:contains(New File):not(:contains(filename))",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_default_value_input input",
            run: "edit file default value",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover",
            run: "press Enter",
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            async run(helpers) {
                const el = this.anchor;
                openEditorPowerBox(el, { start: nodeSize(el) }); // after the file field
            },
        },
        {
            trigger: ".o-we-powerbox .o-we-command-description:contains(Insert a field)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit Company",
        },
        {
            trigger: "[data-name=company_id] > button.o_model_field_selector_popover_item_relation",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit New Image",
        },
        {
            trigger: ".o_model_field_selector_popover_item_name:contains(New Image)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_default_value_input input",
            run: "edit image default value",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover",
            run: "press Enter",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_report_edition_dynamic_table", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            async run(helpers) {
                const el = this.anchor;
                openEditorPowerBox(el);
            },
        },
        {
            trigger:
                ".o-we-powerbox .o-we-command-description:contains(Insert a table based on a relational field)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit Activities",
        },
        {
            trigger: "[data-name=activity_ids] > button.o_model_field_selector_popover_item_name",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_default_value_input input",
            run: "edit First Column",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover",
            run: "press Enter",
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable table tr td:contains(First Column)",
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable table tr[t-foreach]",
            run() {
                const el = this.anchor;
                const context = JSON.parse(el.getAttribute("oe-context"));
                assertEqual(context.x2many_record.model, "mail.activity");
            },
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable table tr td:contains(Insert a field...)",
            run() {
                openEditorPowerBox(this.anchor);
            },
        },
        {
            trigger: ".o-we-powerbox .o-we-command-description:contains(Insert a field)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_search input",
            run: "edit Summary",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover_item_name:contains(Summary)",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_default_value_input input",
            run: "edit Some Summary",
        },
        {
            trigger: ".o-web-studio-field-dynamic-placeholder .o_model_field_selector_popover",
            run: "press Enter",
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable table td span[t-field='x2many_record.summary']",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_saving_xml_editor_reload", {
    steps: () => [
        {
            trigger: "button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
        {
            trigger: ".o_web_studio_xml_editor .ace_editor",
            run() {
                ace.edit(this.anchor)
                    .getSession()
                    .insert(
                        { row: 2, column: 0 },
                        '<span class="test-added-0">in document view</span>\n'
                    );
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
        {
            trigger: ".o_web_studio_xml_editor .ace_editor",
            run() {
                const aceValue = ace.edit(this.anchor).getSession().getValue();

                assertEqual(
                    normalizeXML(aceValue),
                    normalizeXML(`
                        <t t-name="web_studio.test_report_document">
                            <div><p t-field="doc.name"/></div>
                            <span class="test-added-0">in document view</span>
                            <p><br/></p>
                        </t>`)
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_error_at_loading", {
    steps: () => [
        {
            trigger: "body:not(:has(.o_error_dialog)) .o-web-studio-report-editor",
            run: "click",
        },
        {
            trigger: ":iframe div",
            run() {
                assertEqual(
                    this.anchor.textContent,
                    "The report could not be rendered due to an error"
                );
            },
        },
        {
            trigger: "button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_xml_editor",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_error_at_loading_debug", {
    steps: () => [
        {
            trigger: "body:not(:has(.o_error_dialog)) .o-web-studio-report-editor",
            run: "click",
        },
        {
            trigger: ".o-web-studio-report-container:not(:has(iframe))",
            run: "click",
        },
        {
            trigger: ".o-web-studio-report-container strong:contains(builtins.ValueError)",
            run: "click",
        },
        {
            trigger: "button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_xml_editor",
            run: "click",
        },
        {
            trigger: ".o-web-studio-report-container:not(:has(iframe))",
            run: "click",
        },
        {
            trigger:
                ".o-web-studio-report-container strong:contains(odoo.addons.base.models.ir_qweb.QWebException)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_xml_and_form_diff", {
    steps: () => [
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable p:eq(2)",
            run() {
                insertText(this.anchor, "edited with odooEditor");
            },
        },
        {
            trigger: "button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_xml_resource_select_menu button.o_select_menu_toggler .o_select_menu_toggler_slot",
            run() {
                const currentViewKey = this.anchor.textContent.split(" (")[0];
                assertEqual(
                    currentViewKey,
                    "web_studio.report_editor_customization_diff.view._web_studio.test_report_document"
                );
            },
        },
        {
            trigger: ".o_web_studio_xml_resource_select_menu button.o_select_menu_toggler",
            run: "click",
        },
        {
            trigger:
                ".o-dropdown--menu .o_select_menu_item_label:contains(web_studio.test_report_document)",
            run: "click",
        },
        {
            trigger: "button[name='view_diff']",
            run: "click",
        },
        {
            trigger: ".o_form_view table.diff",
            run() {
                assertEqual(
                    document.querySelector(".o_form_view .o_field_widget[name='view_name']")
                        .textContent,
                    "web_studio.test_report_document"
                );
                assertEqual(
                    document.querySelector(
                        ".o_form_view .o_field_widget[name='compare_view_id'] input"
                    ).value,
                    "web_studio_backup__web_studio.test_report_document"
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_record_model_differs_from_action", {
    steps: () => {
        const stepsToAssert = [];

        return [
            {
                trigger: ".o_studio_report_kanban_view",
                run() {
                    const { ReportEditorModel } = odoo.loader.modules.get(
                        "@web_studio/client_action/report_editor/report_editor_model"
                    );

                    patch(ReportEditorModel.prototype, {
                        async loadReportEditor() {
                            await super.loadReportEditor(...arguments);
                            stepsToAssert.push(
                                `report editor loaded. actionModel: "${this._services.studio.editedAction.res_model}". reportModel: "${this.reportResModel}"`
                            );
                        },
                    });
                },
            },
            {
                trigger: ".o_studio_report_kanban_view .o_searchview input",
                run: "fill dummy test",
            },
            {
                trigger:
                    ".o_studio_report_kanban_view .o_searchview .o_menu_item:contains(Report):contains(dummy test)",
                run: "click",
            },
            {
                trigger: ".o_facet_remove",
                run: "click",
            },
            {
                trigger: ".o_kanban_record:contains(dummy test)",
                run: "click",
            },
            {
                trigger: ".o-web-studio-report-editor-wysiwyg",
                run() {
                    assertEqual(
                        JSON.stringify(stepsToAssert),
                        JSON.stringify([
                            `report editor loaded. actionModel: "res.partner". reportModel: "x_dummy.test"`,
                        ])
                    );
                },
            },
        ];
    },
});

registry.category("web_tour.tours").add("web_studio.test_remove_branding_on_copy", {
    steps: () => [
        {
            trigger: "body :iframe .odoo-editor-editable#wrapwrap",
            async run() {
                const doc = this.anchor.ownerDocument;
                const editor = editorsWeakMap.get(doc);
                const originNode = this.anchor.querySelector(`[ws-view-id]`);
                const copy = originNode.cloneNode(true);
                originNode.insertAdjacentElement("afterend", copy);
                editor.shared.history.addStep();
                // Wait for a full macrotask tick and a frame to let the mutation observer
                // of the ReportEditorWysiwyg to catch up on the change and finish its operations
                await nextTick();
                const attributeCopy = {};
                for (const attr of copy.attributes) {
                    attributeCopy[attr.name] = attr.value;
                }
                assertEqual(JSON.stringify(attributeCopy), `{"contenteditable":"true"}`);
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_different_view_document_name", {
    steps: () => [
        {
            trigger: ".o_web_studio_sidebar button[name='report_edit_sources']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_xml_resource_selector .o_select_menu_toggler",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu",
            run() {
                const sources = Array.from(this.anchor.querySelectorAll(".o_select_menu_item")).map(
                    (e) => e.textContent
                );
                assertEqual(
                    sources.includes(
                        "Uses: web_studio.test_report_document (web_studio.test_report_document_1)"
                    ),
                    true
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_edit_main_arch", {
    steps: () => [
        {
            trigger: ":iframe .odoo-editor-editable .outside-t-call",
            async run() {
                const doc = this.anchor.ownerDocument;
                const editor = editorsWeakMap.get(doc);
                const newNode = doc.createElement("div");
                newNode.classList.add("added");
                this.anchor.insertAdjacentElement("beforebegin", newNode);
                editor.shared.history.addStep();
                await nextTick();
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_edit_in_t_call", {
    steps: () => [
        {
            trigger: ":iframe .odoo-editor-editable .in-t-call",
            async run() {
                const doc = this.anchor.ownerDocument;
                const editor = editorsWeakMap.get(doc);
                const newNode = doc.createElement("div");
                newNode.classList.add("added");
                this.anchor.insertAdjacentElement("beforebegin", newNode);
                editor.shared.history.addStep();
                await nextTick();
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_edit_main_and_in_t_call", {
    steps: () => [
        {
            trigger: ":iframe .odoo-editor-editable#wrapwrap",
            async run() {
                const doc = this.anchor.ownerDocument;
                const editor = editorsWeakMap.get(doc);
                const newNode0 = doc.createElement("div");
                newNode0.classList.add("added0");
                const target0 = this.anchor.querySelector(".outside-t-call");
                target0.insertAdjacentElement("beforebegin", newNode0);
                editor.shared.history.addStep();
                await nextTick();
                const newNode1 = doc.createElement("div");
                newNode1.classList.add("added1");
                const target1 = this.anchor.querySelector(".in-t-call");
                target1.insertAdjacentElement("beforebegin", newNode1);
                editor.shared.history.addStep();
                await nextTick();
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_image_crop", {
    steps: () => [
        {
            trigger: "body :iframe .odoo-editor-editable .myimg",
            run: "click",
        },
        {
            trigger: ".o-we-toolbar button[name='image_crop']",
            run: "click",
        },
        {
            trigger: ".o-main-components-container .o_we_crop_widget .cropper-container",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_translations_are_copied", {
    steps: () => [
        {
            trigger: "body :iframe .odoo-editor-editable#wrapwrap div:contains(term2)",
            run() {
                const doc = this.anchor.ownerDocument;
                const editor = editorsWeakMap.get(doc);
                const newNode = doc.createElement("div");
                (newNode.textContent = "term3 from edition"),
                    this.anchor.insertAdjacentElement("beforebegin", newNode);
                editor.shared.history.addStep();
                return nextTick();
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_reports_view_concurrence", {
    steps: () => [
        {
            trigger: ".o_menu_sections li:contains('Reports')",
            run: "click",
        },
        {
            trigger: ".o_kanban_record[data-id] ",
            run: "dblclick",
        },
        {
            trigger: ".o-web-studio-report-editor",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_dont_translate_on_save", {
    steps: () => [
        {
            trigger: "body :iframe .odoo-editor-editable#wrapwrap p.test-origin",
            async run() {
                const doc = this.anchor.ownerDocument;
                const el = doc.createElement("span");
                el.textContent = "new content";
                this.anchor.insertAdjacentElement("beforebegin", el);
                const editor = editorsWeakMap.get(doc);
                editor.shared.history.addStep();
                await nextTick();
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
        {
            trigger: "body :iframe .odoo-editor-editable#wrapwrap span",
            run() {
                const doc = this.anchor.ownerDocument;
                const selection = doc.getSelection();
                selection.removeAllRanges();
                const range = doc.createRange();
                range.selectNode(this.anchor);
                selection.addRange(range);
            },
        },
        {
            trigger: ".o-we-toolbar button[name='bold']",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_do_not_delete_unspecial_spans", {
    steps: () => [
        {
            trigger: "body :iframe .odoo-editor-editable#wrapwrap span",
            run() {
                insertText(this.anchor, "added");
            },
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_edit_header_only_company", {
    steps: () => [
        {
            trigger: "body :iframe .odoo-editor-editable#wrapwrap .header img",
            run() {
                const el = this.anchor;
                const span = el.ownerDocument.createElement("span");
                span.classList.add("studio-added");
                el.insertAdjacentElement("afterend", span);
                openEditorPowerBox(span);
            },
        },
        {
            trigger: ".o-we-powerbox .o-we-command:contains(Insert a field)",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover_item_name:contains(Company ID)",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_default_value_input input",
            run: "edit studio company id",
        },
        {
            trigger: ".o_model_field_selector_popover button:contains(Insert)",
            run: "click",
        },
        {
            trigger:
                "body :iframe .odoo-editor-editable#wrapwrap .header [t-field]:contains(studio company id)",
        },
        {
            trigger: ".o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            trigger: ".o-web-studio-save-report:not(.btn-primary)",
        },
    ],
});
