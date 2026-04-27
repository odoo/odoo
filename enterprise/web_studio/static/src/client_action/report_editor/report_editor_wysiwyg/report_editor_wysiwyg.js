/** @odoo-module */
import {
    Component,
    onWillStart,
    onMounted,
    onWillDestroy,
    onWillUnmount,
    reactive,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { ensureJQuery } from "@web/core/ensure_jquery";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { omit } from "@web/core/utils/objects";
import { usePopover } from "@web/core/popover/popover_hook";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { sortBy } from "@web/core/utils/arrays";
import { useChildRef, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { SelectMenu } from "@web/core/select_menu/select_menu";

import { StudioDynamicPlaceholderPopover } from "./studio_dynamic_placeholder_popover";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { CharField } from "@web/views/fields/char/char_field";
import { Record as _Record } from "@web/model/record";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { ReportEditorSnackbar } from "@web_studio/client_action/report_editor/report_editor_snackbar";
import { useEditorMenuItem } from "@web_studio/client_action/editor/edition_flow";
import { memoizeOnce } from "@web_studio/client_action/utils";
import { ReportEditorIframe } from "../report_editor_iframe";
import { Editor } from "@html_editor/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { nodeSize } from "@html_editor/utils/position";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { QWebTablePlugin } from "./qweb_table_plugin";
import { visitNode } from "../utils";
import { TablePlugin } from "@html_editor/main/table/table_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { uniqueId } from "@web/core/utils/functions";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";

/**
 * @typedef {Object} QwebVariableInfo
 * @property {string} model - The technical model name (e.g. "res.partner").
 * @property {string} name - The human-readable model name.
 * @property {boolean} in_foreach - Whether the variable appears inside a `t-foreach`.
 */

/**
 * @typedef {Record<string, QwebVariableInfo>} AvailableQwebVariables
 */

class __Record extends _Record.components._Record {
    setup() {
        super.setup();
        const willSaveUrgently = () => this.model.bus.trigger("WILL_SAVE_URGENTLY");
        onMounted(() => {
            this.env.reportEditorModel.bus.addEventListener("WILL_SAVE_URGENTLY", willSaveUrgently);
        });

        onWillDestroy(() =>
            this.env.reportEditorModel.bus.removeEventListener(
                "WILL_SAVE_URGENTLY",
                willSaveUrgently
            )
        );
    }
}

class Record extends _Record {
    static components = { ..._Record.components, _Record: __Record };
}

function getOrderedTAs(node) {
    const results = [];
    while (node) {
        const closest = node.closest("[t-foreach]");
        if (closest) {
            results.push(closest.getAttribute("t-as"));
            node = closest.parentElement;
        } else {
            node = null;
        }
    }
    return results;
}

class FieldDynamicPlaceholder extends Component {
    static components = { StudioDynamicPlaceholderPopover, SelectMenu };
    static template = "web_studio.FieldDynamicPlaceholder";
    static props = {
        resModel: String,
        availableQwebVariables: Object,
        close: Function,
        validate: Function,
        initialQwebVar: String,
        showOnlyX2ManyFields: Boolean,
        sortedVariables: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    label: { type: String },
                    value: { type: String },
                },
            },
        },
    };

    setup() {
        this.state = useState({ currentVar: this.props.initialQwebVar });
        useHotkey("escape", () => this.props.close());
    }

    get currentResModel() {
        const currentVar = this.state.currentVar;
        const resModel = currentVar && this.props.availableQwebVariables[currentVar].model;
        return resModel || this.props.resModel;
    }

    validate(...args) {
        this.props.validate(this.state.currentVar, ...args);
    }
}

class UndoRedo extends Component {
    static template = "web_studio.ReportEditorWysiwyg.UndoRedo";
    static props = {
        state: Object,
    };
}

class ResetConfirmationPopup extends ConfirmationDialog {
    static template = "web_studio.ReportEditorWysiwyg.ResetConfirmationPopup";
    static props = {
        ...omit(ConfirmationDialog.props, "body"),
        state: Object,
    };
}

const CUSTOM_BRANDING_ATTR = [
    "ws-view-id",
    "ws-call-key",
    "ws-call-group-key",
    "ws-real-children",
    "o-diff-key",
];

class _TablePlugin extends TablePlugin {
    static id = TablePlugin.id;
    _insertTable() {
        const table = super._insertTable(...arguments);
        if (closestElement(table, "[t-call='web.external_layout']")) {
            table.removeAttribute("class");
            table.classList.add("table", "o_table", "table-borderless");
        }
        return table;
    }
}

const EXCLUDED_PLUGIN_IDS = new Set(["powerButtons"]);
const REPORT_EDITOR_PLUGINS_MAP = Object.fromEntries(
    MAIN_PLUGINS.filter((cls) => !EXCLUDED_PLUGIN_IDS.has(cls.id)).map((cls) => [cls.id, cls])
);
Object.assign(REPORT_EDITOR_PLUGINS_MAP, {
    [QWebPlugin.id]: QWebPlugin,
    [QWebTablePlugin.id]: QWebTablePlugin,
    [TablePlugin.id]: _TablePlugin,
});

export class ReportEditorWysiwyg extends Component {
    static components = {
        CharField,
        Record,
        Many2ManyTagsField,
        Many2OneField,
        BooleanField,
        UndoRedo,
        ReportEditorIframe,
        LocalOverlayContainer,
    };
    static props = {
        paperFormatStyle: String,
    };
    static template = "web_studio.ReportEditorWysiwyg";

    setup() {
        this.overlayRef = useChildRef();
        useSubEnv({
            localOverlayContainerKey: uniqueId("report_editor"),
        });
        this.action = useService("action");
        this.addDialog = useOwnedDialogs();
        this.notification = useService("notification");

        this._getReportQweb = memoizeOnce(() => {
            const tree = new DOMParser().parseFromString(
                this.reportEditorModel.reportQweb,
                "text/html"
            );
            const htmlNode = tree.firstElementChild;
            htmlNode.translate = false;
            return htmlNode;
        });

        const reportEditorModel = (this.reportEditorModel = useState(this.env.reportEditorModel));

        this.fieldPopover = usePopover(FieldDynamicPlaceholder);
        useEditorMenuItem({
            component: ReportEditorSnackbar,
            props: {
                state: reportEditorModel,
                onSave: this.save.bind(this),
                onDiscard: this.discard.bind(this),
            },
        });

        // This little reactive is to be bound to the editor, so we create it here.
        // This could have been a useState, but the current component doesn't use it.
        // Instead, it passes it to a child of his,
        this.undoRedoState = reactive({
            canUndo: false,
            canRedo: false,
            undo: () => this.editor?.shared.history.undo(),
            redo: () => this.editor?.shared.history.redo(),
        });

        onWillStart(async () => {
            await ensureJQuery();
            await Promise.all([
                loadBundle("web_editor.backend_assets_wysiwyg"),
                this.reportEditorModel.loadReportQweb(),
            ]);
        });

        onWillUnmount(() => {
            this.reportEditorModel.bus.trigger("WILL_SAVE_URGENTLY");
            this.save({ urgent: true });
            if (this.editor) {
                this.editor.destroy(true);
            }
        });
    }

    instantiateEditor({ editable } = {}) {
        this.undoRedoState.canUndo = false;
        this.undoRedoState.canRedo = false;
        const onEditorChange = () => {
            const canUndo = this.editor.shared.history.canUndo();
            this.reportEditorModel.isDirty = canUndo;
            Object.assign(this.undoRedoState, {
                canUndo: canUndo,
                canRedo: this.editor.shared.history.canRedo(),
            });
        };

        editable.querySelectorAll("[ws-view-id]").forEach((el) => {
            el.setAttribute("contenteditable", "true");
        });

        const editor = new Editor(
            {
                Plugins: Object.values(REPORT_EDITOR_PLUGINS_MAP),
                onChange: onEditorChange,
                getRecordInfo: () => {
                    const { anchorNode } = this.editor.shared.selection.getEditableSelection();
                    if (!anchorNode) {
                        return {};
                    }
                    const lastViewParent = closestElement(anchorNode, "[ws-view-id]");
                    if (!lastViewParent) {
                        return {};
                    }
                    return {
                        resModel: "ir.ui.view",
                        resId: parseInt(lastViewParent.getAttribute("ws-view-id")),
                        field: "arch",
                    };
                },
                resources: {
                    handleNewRecords: this.handleMutations.bind(this),
                    powerbox_categories: withSequence(5, {
                        id: "report_tools",
                        name: _t("Report Tools"),
                    }),
                    user_commands: this.getUserCommands(),
                    powerbox_items: this.getPowerboxCommands(),
                    unsplittable_node_predicates: (node) => {
                        return (
                            node.nodeType === Node.ELEMENT_NODE &&
                            node.matches(".page, .header, .footer")
                        );
                    },
                },
                disableVideo: true,
                allowImageTransform: false,
                allowImageResize: false,
                localOverlayContainers: {
                    key: this.env.localOverlayContainerKey,
                    ref: this.overlayRef,
                },
            },
            this.env.services
        );
        editor.attachTo(editable);
        // disable the qweb's plugin class: its style is too complex and confusing
        // in the case of reports
        editable.classList.remove("odoo-editor-qweb");
        return editor;
    }

    onIframeLoaded({ iframeRef }) {
        if (this.editor) {
            this.editor.destroy(true);
        }
        this.iframeRef = iframeRef;
        const doc = iframeRef.el.contentDocument;
        doc.body.classList.remove("container");

        if (odoo.debug) {
            ["t-esc", "t-out", "t-field"].forEach((tAtt) => {
                doc.querySelectorAll(`*[${tAtt}]`).forEach((e) => {
                    // Save the previous title to set it back before saving the report
                    if (e.hasAttribute("title")) {
                        e.setAttribute("data-oe-title", e.getAttribute("title"));
                    }
                    e.setAttribute("title", e.getAttribute(tAtt));
                });
            });
        }
        if (!this.reportEditorModel._errorMessage) {
            this.editor = this.instantiateEditor({ editable: doc.querySelector("#wrapwrap") });
        }
        this.reportEditorModel.setInEdition(false);
    }

    handleMutations(records) {
        for (const record of records) {
            if (record.type === "attributes") {
                if (record.attributeName === "contenteditable") {
                    continue;
                }
                if (record.attributeName.startsWith("data-oe-t")) {
                    continue;
                }
            }
            if (record.type === "childList") {
                Array.from(record.addedNodes).forEach((el) => {
                    if (el.nodeType !== 1) {
                        return;
                    }
                    visitNode(el, (node) => {
                        CUSTOM_BRANDING_ATTR.forEach((attr) => {
                            node.removeAttribute(attr);
                        });
                        node.classList.remove("o_dirty");
                    });
                });
                const realRemoved = [...record.removedNodes].filter(
                    (n) => n.nodeType !== Node.COMMENT_NODE
                );
                if (!realRemoved.length && !record.addedNodes.length) {
                    continue;
                }
            }

            let target = record.target;
            if (!target.isConnected) {
                continue;
            }
            if (target.nodeType !== Node.ELEMENT_NODE) {
                target = target.parentElement;
            }
            if (!target) {
                continue;
            }

            target = target.closest(`[ws-view-id]`);
            if (!target) {
                continue;
            }
            if (!target.classList.contains("o_dirty")) {
                target.classList.add("o_dirty");
            }
        }
    }

    get reportQweb() {
        const model = this.reportEditorModel;
        return this._getReportQweb(`${model.renderKey}_${model.reportQweb}`).outerHTML;
    }

    get reportRecordProps() {
        const model = this.reportEditorModel;
        return {
            fields: model.reportFields,
            activeFields: model.reportActiveFields,
            values: model.reportData,
        };
    }

    async save({ urgent = false } = {}) {
        if (!this.editor) {
            await this.reportEditorModel.saveReport({ urgent });
            return;
        }
        const htmlParts = {};
        const editable = this.editor.getElContent();

        // Clean technical title
        if (odoo.debug) {
            editable.querySelectorAll("*[t-field],*[t-out],*[t-esc]").forEach((e) => {
                if (e.hasAttribute("data-oe-title")) {
                    e.setAttribute("title", e.getAttribute("data-oe-title"));
                    e.removeAttribute("data-oe-title");
                } else {
                    e.removeAttribute("title");
                }
            });
        }

        editable.querySelectorAll("[ws-view-id].o_dirty").forEach((el) => {
            el.classList.remove("o_dirty");
            el.removeAttribute("contenteditable");
            const viewId = el.getAttribute("ws-view-id");
            if (!viewId) {
                return;
            }
            Array.from(el.querySelectorAll("[t-call]")).forEach((el) => {
                el.removeAttribute("contenteditable");
                el.replaceChildren();
            });

            Array.from(el.querySelectorAll("[oe-origin-t-out]")).forEach((el) => {
                el.replaceChildren();
            });
            if (!el.hasAttribute("oe-origin-class") && el.getAttribute("class") === "") {
                el.removeAttribute("class");
            }

            const callGroupKey = el.getAttribute("ws-call-group-key");
            const type = callGroupKey ? "in_t_call" : "full";

            const escaped_html = el.outerHTML;
            htmlParts[viewId] = htmlParts[viewId] || [];

            htmlParts[viewId].push({
                call_key: el.getAttribute("ws-call-key"),
                call_group_key: callGroupKey,
                type,
                html: escaped_html,
            });
        });
        await this.reportEditorModel.saveReport({ htmlParts, urgent });
    }

    async discard() {
        if (this.editor) {
            const selection = this.editor.document.getSelection();
            if (selection) {
                selection.removeAllRanges();
            }
        }
        this.env.services.dialog.add(ConfirmationDialog, {
            body: _t(
                "If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."
            ),
            confirm: () => this.reportEditorModel.discardReport(),
            cancel: () => {},
        });
    }

    getUserCommands() {
        const isAvailable = (selection) => {
            const { availableQwebVariables, initialQwebVar, isEditingFooterHeader } =
                this.getQwebVariables(this.getPopoverAnchor(selection));

            return !!this.getDefaultVariable(
                initialQwebVar,
                availableQwebVariables,
                isEditingFooterHeader
            );
        };
        return [
            {
                id: "insertField",
                title: _t("Field"),
                description: _t("Insert a field"),
                icon: "fa-magic",
                run: this.insertField.bind(this),
                isAvailable,
            },
            {
                id: "insertDynamicTable",
                title: _t("Dynamic Table"),
                description: _t("Insert a table based on a relational field."),
                icon: "fa-magic",
                run: this.insertTableX2Many.bind(this),
                isAvailable,
            },
        ];
    }

    getPowerboxCommands() {
        return [
            withSequence(20, {
                categoryId: "report_tools",
                commandId: "insertField",
            }),
            withSequence(25, {
                categoryId: "report_tools",
                commandId: "insertDynamicTable",
            }),
        ];
    }

    /**
     * @param {HTMLElement} element
     * @return {{isEditingFooterHeader: boolean, availableQwebVariables: AvailableQwebVariables, initialQwebVar: string} | {}}
     */
    getQwebVariables(element) {
        if (!element) {
            return {};
        }
        const nodeOeContext = element.closest("[oe-context]");

        /** @type {AvailableQwebVariables} */
        let availableQwebVariables =
            (nodeOeContext && JSON.parse(nodeOeContext.getAttribute("oe-context"))) || {};

        const isEditingFooterHeader = !!closestElement(element, ".header,.footer");
        let initialQwebVar;
        if (isEditingFooterHeader) {
            const companyVars = Object.entries(availableQwebVariables).filter(
                ([k, v]) => v.model === "res.company"
            );
            initialQwebVar = companyVars[0]?.[0];
            availableQwebVariables = Object.fromEntries(companyVars);
        } else {
            initialQwebVar = getOrderedTAs(element)[0] || "";
        }
        return {
            isEditingFooterHeader,
            availableQwebVariables,
            initialQwebVar,
        };
    }

    /**
     * @param {AvailableQwebVariables} availableQwebVariables
     * @param {boolean} isEditingFooterHeader
     * @param {string} resModel
     * @return {{label: string, value: string}[]}
     */
    sortedVariables(availableQwebVariables, isEditingFooterHeader, resModel) {
        const entries = Object.entries(availableQwebVariables).filter(
            ([k, v]) => v.in_foreach && !isEditingFooterHeader
        );
        const sortFn = ([k, v]) => {
            let score = 0;
            if (k === "doc") {
                score += 2;
            }
            if (k === "docs") {
                score -= 2;
            }
            if (k === "o") {
                score++;
            }
            if (v.model === resModel) {
                score++;
            }
            return score;
        };

        const mapFn = ([k, v]) => {
            return {
                value: k,
                label: `${k} (${v.name})`,
            };
        };
        return sortBy(entries, sortFn, "desc").map((e) => mapFn(e));
    }

    /**
     * @param {string} [initialQwebVar]
     * @param {AvailableQwebVariables} availableQwebVariables
     * @param {boolean} isEditingFooterHeader
     * @return {string|undefined}
     */
    getDefaultVariable(initialQwebVar, availableQwebVariables, isEditingFooterHeader) {
        if (initialQwebVar && initialQwebVar in availableQwebVariables) {
            return initialQwebVar;
        }
        if (isEditingFooterHeader) {
            const companyVar = Object.entries(availableQwebVariables).find(
                ([k, v]) => v.model === "res.company"
            );
            return companyVar && companyVar[0];
        }
        const resModel = this.reportEditorModel.reportResModel;
        const sortedVariables = this.sortedVariables(
            availableQwebVariables,
            isEditingFooterHeader,
            resModel
        );

        let defaultVar = sortedVariables.find((v) => {
            return ["doc", "o"].includes(v.value);
        });
        defaultVar ??= sortedVariables.find(
            (v) => availableQwebVariables[v.value].model === resModel
        );
        return defaultVar && defaultVar.value;
    }

    getFieldPopoverParams() {
        const resModel = this.reportEditorModel.reportResModel;
        const popoverAnchor = this.getPopoverAnchor();
        const { availableQwebVariables, initialQwebVar, isEditingFooterHeader } =
            this.getQwebVariables(popoverAnchor);
        const sortedVariables = this.sortedVariables(
            availableQwebVariables,
            isEditingFooterHeader,
            resModel
        );
        const defaultVariable = this.getDefaultVariable(
            initialQwebVar,
            availableQwebVariables,
            isEditingFooterHeader
        );
        return {
            popoverAnchor,
            props: {
                availableQwebVariables,
                initialQwebVar: defaultVariable,
                resModel,
                sortedVariables,
            },
        };
    }

    getPopoverAnchor(selection) {
        selection ||= this.editor.shared.selection.getEditableSelection();
        const { anchorNode } = selection;
        return anchorNode.nodeType === 1 ? anchorNode : anchorNode.parentElement;
    }

    async insertTableX2Many() {
        const { popoverAnchor, props } = this.getFieldPopoverParams();
        await this.fieldPopover.open(popoverAnchor, {
            ...props,
            showOnlyX2ManyFields: true,
            validate: (
                qwebVar,
                fieldNameChain,
                defaultValue = "",
                is_image,
                relation,
                relationName
            ) => {
                const doc = this.editor.document;
                doc.defaultView.focus();

                const table = doc.createElement("table");
                table.classList.add("table", "table-sm");

                const tBody = table.createTBody();

                const topRow = tBody.insertRow();
                topRow.classList.add(
                    "border-bottom",
                    "border-top-0",
                    "border-start-0",
                    "border-end-0",
                    "border-2",
                    "border-dark",
                    "fw-bold"
                );
                const topTd = doc.createElement("td");
                topTd.appendChild(doc.createTextNode(defaultValue || "Column name"));
                topRow.appendChild(topTd);

                const tr = doc.createElement("tr");
                tr.setAttribute("t-foreach", `${qwebVar}.${fieldNameChain}`);
                tr.setAttribute("t-as", "x2many_record");
                tr.setAttribute(
                    "oe-context",
                    JSON.stringify({
                        x2many_record: {
                            model: relation,
                            in_foreach: true,
                            name: relationName,
                        },
                        ...props.availableQwebVariables,
                    })
                );
                tBody.appendChild(tr);

                const td = doc.createElement("td");
                td.textContent = _t("Insert a field...");
                tr.appendChild(td);

                this.editor.shared.dom.insert(table);
                this.editor.shared.selection.setSelection({
                    anchorNode: td,
                    focusOffset: nodeSize(td),
                });
                this.editor.shared.history.addStep();
            },
        });
    }

    async insertField() {
        const { popoverAnchor, props } = this.getFieldPopoverParams();
        await this.fieldPopover.open(popoverAnchor, {
            ...props,
            showOnlyX2ManyFields: false,
            validate: (
                qwebVar,
                fieldNameChain,
                defaultValue = "",
                is_image,
                relation,
                fieldString
            ) => {
                const doc = this.editor.document;
                doc.defaultView.focus();

                const span = doc.createElement("span");
                span.setAttribute(
                    "oe-expression-readable",
                    fieldString || `field: "${qwebVar}.${fieldNameChain}"`
                );
                span.textContent = defaultValue;
                span.setAttribute("t-field", `${qwebVar}.${fieldNameChain}`);

                if (odoo.debug) {
                    span.setAttribute("title", `${qwebVar}.${fieldNameChain}`);
                }

                if (is_image) {
                    span.setAttribute("t-options-widget", "'image'");
                    span.setAttribute("t-options-qweb_img_raw_data", 1);
                }
                this.editor.shared.dom.insert(span);
                this.editor.shared.history.addStep();
            },
        });
    }

    async printPreview() {
        const model = this.reportEditorModel;
        await this.save();
        const recordId = model.reportEnv.currentId || model.reportEnv.ids.find((i) => !!i) || false;
        if (!recordId) {
            this.notification.add(
                _t(
                    "There is no record on which this report can be previewed. Create at least one record to preview the report."
                ),
                {
                    type: "danger",
                    title: _t("Report preview not available"),
                }
            );
            return;
        }

        const action = await rpc("/web_studio/print_report", {
            record_id: recordId,
            report_id: model.editedReportId,
        });
        this.reportEditorModel.renderKey++;
        return this.action.doAction(action, { clearBreadcrumbs: true });
    }

    async resetReport() {
        const state = reactive({ includeHeaderFooter: true });
        this.addDialog(ResetConfirmationPopup, {
            title: _t("Reset report"),
            confirmLabel: _t("Reset report"),
            confirmClass: "btn-danger",
            cancelLabel: _t("Go back"),
            state,
            cancel: () => {},
            confirm: async () => {
                await this.reportEditorModel.saveReport();
                try {
                    await this.reportEditorModel.resetReport(state.includeHeaderFooter);
                } finally {
                    this.reportEditorModel.renderKey++;
                }
            },
        });
    }

    async openReportFormView() {
        await this.save();
        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "ir.actions.report",
                res_id: this.reportEditorModel.editedReportId,
                views: [[false, "form"]],
                target: "current",
            },
            { clearBreadcrumbs: true }
        );
    }

    async editSources() {
        await this.save();
        this.reportEditorModel.mode = "xml";
    }
}
