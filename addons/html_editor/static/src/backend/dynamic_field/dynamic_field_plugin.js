import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { isContentEditable } from "@html_editor/utils/dom_info";
import { closestElement, traverseNode } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

import { FieldSelectorPopover } from "@html_editor/backend/dynamic_field/field_selector_popover";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { Plugin } from "@html_editor/plugin";

const QWEB_T_OUT = ["t-field", "t-out", "t-esc"];
const DUMMY_CONTENT_ATTRS = ["data-oe-demo", "data-oe-expression-readable"];

export class DynamicFieldPlugin extends Plugin {
    static id = "dynamicField";
    static dependencies = ["selection", "history", "overlay", "dom", "toolbar", QWebPlugin.id];

    /** @type {import("plugins").EditorResources} */
    resources = {
        toolbar_groups: withSequence(9, { id: "dynamic_field" }),
        toolbar_items: [
            {
                id: "editDynamicField",
                groupId: "dynamic_field",
                namespaces: ["compact", "expanded"],
                commandId: "editDynamicField",
            },
        ],
        user_commands: [
            {
                id: "insertField",
                title: _t("Field"),
                description: _t("Insert a field"),
                icon: "fa-database",
                run: this.insertField.bind(this),
                isAvailable: (selection) => isHtmlContentSupported(selection),
            },
            {
                id: "editDynamicField",
                title: _t("Edit field"),
                description: _t("Change the placeholder or the expression for an existing field"),
                icon: "fa-pencil",
                run: this.editField.bind(this),
                isAvailable: () => !!this.getPopoverTarget(true),
            },
        ],
        powerbox_categories: withSequence(1, {
            id: "dynamic_field_tools",
            name: _t("Data"),
        }),
        powerbox_items: [
            withSequence(20, {
                categoryId: "dynamic_field_tools",
                commandId: "insertField",
            }),
        ],
        selectionchange_handlers: withSequence(9, this.onSelectionChanged.bind(this)),
        dynamic_model_change_handlers: this.updateDynamicModel.bind(this),
        normalize_handlers: withSequence(11, this.normalizeQwebPlaceholders.bind(this)),
        clipboard_content_processors: withSequence(11, this.cleanQwebExpressionsForCopy.bind(this)),
        clean_for_save_handlers: withSequence(11, this.cleanQwebExpressionsForSave.bind(this)),
    };

    fieldTagName = "T";
    fieldAttribute = "t-out";

    setup() {
        this.resModel = this.config.dynamicResModel;

        this.fieldPopover = this.dependencies.overlay.createOverlay(FieldSelectorPopover, {
            hasAutofocus: true,
            editable: this.editable,
            className: "bg-light rounded border shadow",
        });

        this.addDomListener(
            this.editable,
            "click",
            (ev) => {
                if (ev.detail === 1 && this.isSelectable(ev.target)) {
                    this.dependencies.selection.selectElement(ev.target);
                }
            },
            true
        );
    }

    isValidTargetForDomListener(ev) {
        return (
            (ev.type === "click" &&
                ev.target &&
                closestElement(ev.target, `[${this.fieldAttribute}]`)) ||
            super.isValidTargetForDomListener(ev)
        );
    }

    updateDynamicModel(resModel) {
        this.resModel = resModel;
    }

    getPopoverTarget(isEdit) {
        if (isEdit) {
            const elements = this.dependencies.selection
                .getTargetedNodes()
                .filter((n) => n.nodeType === Node.ELEMENT_NODE);

            if (elements.length === 1 && elements[0].hasAttribute(this.fieldAttribute)) {
                // For now, ban expressions that contain a parenthesis
                // That would be a function call (usually sudo)
                // but we are *really* not sure about this.
                if (elements[0].getAttribute(this.fieldAttribute).includes("(")) {
                    return;
                }
                return elements[0];
            }
        } else {
            const { anchorNode } = this.dependencies.selection.getEditableSelection();
            return anchorNode.nodeType === Node.ELEMENT_NODE
                ? anchorNode
                : anchorNode.parentElement;
        }
    }

    async editField() {
        const target = this.getPopoverTarget(true);
        if (!target) {
            return;
        }

        await this.config.dynamicFieldPreprocess?.({
            resModel: this.resModel,
            element: target,
        });

        const resModel = this.getResModel(target);
        const fullPath = target.getAttribute(this.fieldAttribute) || "";
        const initialPath = fullPath.substring(fullPath.indexOf(".") + 1);

        const initialLabel =
            target.innerText ||
            target.getAttribute("data-oe-demo") ||
            target.getAttribute("data-oe-expression-readable");

        this.fieldPopover.open({
            target,
            props: {
                resModel,
                path: initialPath,
                label: initialLabel,
                filter: this.filter.bind(this),
                close: () => this.fieldPopover.close(),
                validate: async ({ path, label, fieldInfo }) => {
                    if (path !== initialPath) {
                        const fullPath = this.getFieldPath(target, path);
                        await this.setFieldAttributes(target, path, fullPath, fieldInfo);
                        await this.config.dynamicFieldPostprocess?.({
                            path: fullPath,
                            label,
                            fieldInfo,
                            resModel,
                            element: target,
                        });
                    }

                    if (label !== initialLabel) {
                        target.setAttribute("data-oe-demo", label);
                        const prevText = target.textContent;
                        this.dependencies.history.applyCustomMutation({
                            apply: () => {
                                target.textContent = "";
                                this.normalizeQwebPlaceholders(target);
                                this.dispatchTo("dynamic_field_edit_apply_handlers", target);
                            },
                            revert: () => {
                                target.textContent = prevText;
                            },
                        });
                    }

                    if (path !== initialPath || label !== initialLabel) {
                        this.dependencies.history.addStep();
                    }
                },
            },
        });
    }

    async insertField() {
        await this.config.dynamicFieldPreprocess?.({
            resModel: this.resModel,
            element: null,
        });

        const target = this.getPopoverTarget(false);
        const resModel = this.getResModel(target);
        this.fieldPopover.open({
            target,
            props: {
                resModel,
                filter: this.filter.bind(this),
                close: () => this.fieldPopover.close(),
                validate: async ({ path, label, fieldInfo }) => {
                    const doc = this.document;
                    doc.defaultView.focus();

                    const selection = this.dependencies.selection.preserveSelection();

                    const el = this.document.createElement(this.fieldTagName);
                    const fullPath = this.getFieldPath(target, path);
                    await this.setFieldAttributes(el, path, fullPath, fieldInfo);
                    el.setAttribute("data-oe-demo", label);
                    el.innerText = label;

                    await this.config.dynamicFieldPostprocess?.({
                        path: fullPath,
                        label,
                        fieldInfo,
                        resModel,
                        element: el,
                    });

                    selection.restore();
                    this.dependencies.dom.insert(el);
                    this.dependencies.history.addStep();
                },
            },
        });
    }

    filter(fieldDef, path) {
        if (fieldDef.is_property && fieldDef.type === "separator") {
            return false;
        }
        if (this.config.dynamicFieldFilter && !this.config.dynamicFieldFilter(fieldDef, path)) {
            return false;
        }
        return !["one2many", "boolean", "many2many"].includes(fieldDef.type);
    }

    getResModel(element) {
        return this.resModel;
    }

    getFieldPath(element, fieldPath) {
        return `object.${fieldPath}`;
    }

    async setFieldAttributes(el, fieldPath, fullPath, fieldInfo) {
        if (odoo.debug) {
            el.setAttribute("title", `${fullPath}`);
        }

        el.setAttribute("data-oe-expression-readable", fieldInfo.string || `field: "${fullPath}"`);
        el.setAttribute(this.fieldAttribute, fullPath);

        if (await this.isImage(fieldPath, fieldInfo)) {
            el.setAttribute("t-options-widget", "'image'");
            el.setAttribute("t-options-qweb_img_raw_data", 1);
        }
    }

    async isImage(fieldPath, fieldInfo) {
        const filenameExists = (
            await this.services.field.loadFieldInfo(this.resModel, fieldPath + "_filename")
        ).fieldDef;
        return fieldInfo.type == "binary" && !filenameExists;
    }

    onSelectionChanged(selectionData) {
        const selection = selectionData.documentSelection;
        if (!selection) {
            return;
        }
        const node = selection.anchorNode;
        const parent = closestElement(node, "[data-oe-expression-readable]");
        if (parent && parent !== node && this.isSelectable(parent)) {
            this.dependencies.selection.selectElement(parent);
        }
    }

    isSelectable(element) {
        return (
            element.getAttribute("data-oe-expression-readable") &&
            !isContentEditable(element) &&
            this.editable.contains(element)
        );
    }

    normalizeQwebPlaceholders(node) {
        traverseNode(node, (el) => {
            if (!QWEB_T_OUT.some((att) => el.hasAttribute(att))) {
                return true;
            }

            for (const dummyAttr of DUMMY_CONTENT_ATTRS) {
                if (!el.textContent.trim() && el.hasAttribute(dummyAttr)) {
                    el.appendChild(this.document.createTextNode(el.getAttribute(dummyAttr)));
                }
            }
            return false;
        });
    }

    cleanQwebExpressionsForCopy(node) {
        Array.from(node.querySelectorAll("[data-oe-expression-readable],[data-oe-demo]")).forEach(
            (el) => {
                if (QWEB_T_OUT.some((attr) => el.hasAttribute(attr))) {
                    el.replaceChildren();
                }
            }
        );
    }

    cleanQwebExpressionsForSave({ root }) {
        traverseNode(root, (el) => {
            let doChildren = true;
            for (const dummyAttr of DUMMY_CONTENT_ATTRS) {
                if (el.hasAttribute(dummyAttr)) {
                    if (el.textContent.trim() === el.getAttribute(dummyAttr)) {
                        el.replaceChildren();
                    }
                    doChildren = false;
                }
            }
            return doChildren;
        });
    }
}

export const DYNAMIC_FIELD_PLUGINS = [QWebPlugin, DynamicFieldPlugin];
