import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { FieldSelectorPopover } from "./field_selector_popover";

export class DynamicTablePlugin extends Plugin {
    static id = "dynamic_table";
    static dependencies = [
        "selection",
        "history",
        "overlay",
        "dom",
        "toolbar",
        "selection",
        "dynamicField",
    ];

    resources = {
        user_commands: [
            {
                id: "insertDynamicTable",
                title: _t("Dynamic Table"),
                description: _t("Insert a table based on a relational field."),
                icon: "fa-database",
                run: this.insertTable.bind(this),
                isAvailable: (selection) => this.isInsertAvailable(selection),
            },
        ],
        powerbox_items: [
            withSequence(25, {
                categoryId: "dynamic_field_tools",
                commandId: "insertDynamicTable",
            }),
        ],
        dynamic_model_change_handlers: this.updateDynamicModel.bind(this),
        after_insert_handlers: this.elementInsertedHandler.bind(this),
    };

    setup() {
        this.resModel = this.config.dynamicResModel;
        this.fieldPopover = this.dependencies.overlay.createOverlay(FieldSelectorPopover, {
            hasAutofocus: true,
            editable: this.editable,
            className: "bg-light rounded border shadow",
        });
    }

    isInsertAvailable(selection) {
        if (!isHtmlContentSupported(selection)) {
            return false;
        }

        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const target =
            anchorNode.nodeType === Node.ELEMENT_NODE ? anchorNode : anchorNode.parentElement;
        return !!target;
    }

    updateDynamicModel(resModel) {
        this.resModel = resModel;
    }

    async insertTable() {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const target = anchorNode.nodeType === 1 ? anchorNode : anchorNode.parentElement;

        const [resModel, basePath] = await this.dependencies.dynamicField.getResModel(target);

        this.fieldPopover.open({
            target,
            props: {
                resModel,
                followRelations: false,
                disableLabel: true,
                filter: (fieldDef, path) => ["one2many", "many2many"].includes(fieldDef.type),
                close: () => this.fieldPopover.close(),
                validate: async ({ path, fieldInfo }) => {
                    const doc = this.document;
                    doc.defaultView.focus();

                    const selection = this.dependencies.selection.preserveSelection();
                    const table = this.document.createElement("table");
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
                    const topTd = this.document.createElement("td");
                    topTd.appendChild(
                        this.document.createTextNode(fieldInfo.string || "Column name")
                    );
                    topRow.appendChild(topTd);

                    const tr = this.createRowElement(target, basePath, path);
                    tBody.appendChild(tr);

                    await this.config.dynamicFieldPostprocess?.({
                        fieldInfo,
                        element: tr,
                    });

                    const td = this.document.createElement("td");
                    td.textContent = _t("Insert a field...");
                    tr.appendChild(td);

                    selection.restore();
                    this.dependencies.dom.insert(table);
                    this.editable.focus();
                    this.dependencies.selection.setSelection({
                        anchorNode: td,
                        focusOffset: nodeSize(td),
                    });
                    this.dependencies.history.addStep();
                },
            },
        });
    }

    createRowElement(target, basePath, path) {
        const tr = this.document.createElement("tr");
        const tAsPrefix = "table_record_";

        let id = 0;
        this.document.querySelectorAll("[t-as], [t-set]").forEach((el) => {
            for (const att of [el.getAttribute("t-as"), el.getAnimations("t-set")]) {
                if (!att.startsWith(tAsPrefix)) {
                    continue;
                }
                const value = parseInt(att.replace(tAsPrefix, ""));
                if (typeof value == "number" && value > id) {
                    id = value + 1;
                }
            }
        });
        tr.setAttribute("t-as", `${tAsPrefix}${id}`);

        tr.setAttribute(
            "t-foreach",
            this.dependencies.dynamicField.getFieldPath(target, basePath, path)
        );
        return tr;
    }

    /**
     * @param {HTMLElement[]} insertedNodes
     */
    elementInsertedHandler(insertedNodes) {
        for (const node of insertedNodes) {
            if (
                node.tagName === "TABLE" &&
                node.classList.contains("o_table") &&
                closestElement(node, "[t-call='web.external_layout']")
            ) {
                node.removeAttribute("class");
                node.classList.add("table", "o_table", "table-borderless");
            }
        }
    }
}
