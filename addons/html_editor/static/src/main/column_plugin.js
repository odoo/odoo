import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";

const REGEX_BOOTSTRAP_COLUMN = /(?:^| )col(-[a-zA-Z]+)?(-\d+)?(?:$| )/;

function isUnremovableColumn(node, root) {
    const isColumnInnerStructure =
        node.nodeName === "DIV" && [...node.classList].some((cls) => /^row$|^col$|^col-/.test(cls));

    if (!isColumnInnerStructure) {
        return false;
    }
    if (!root) {
        return true;
    }
    const closestColumnContainer = closestElement(node, "div.o_text_columns");
    return !root.contains(closestColumnContainer);
}

function columnIsAvailable(numberOfColumns) {
    return (selection) => {
        const row = closestElement(selection.anchorNode, ".o_text_columns .row");
        return !(row && row.childElementCount === numberOfColumns);
    };
}

export class ColumnPlugin extends Plugin {
    static id = "column";
    static dependencies = ["baseContainer", "selection", "history"];
    resources = {
        user_commands: [
            {
                id: "columnize",
                title: _t("Columnize"),
                description: _t("Convert into columns"),
                icon: "fa-columns",
                run: this.columnize.bind(this),
            },
        ],
        powerbox_items: [
            {
                title: _t("2 columns"),
                description: _t("Convert into 2 columns"),
                categoryId: "structure",
                isAvailable: columnIsAvailable(2),
                commandId: "columnize",
                commandParams: { numberOfColumns: 2 },
            },
            {
                title: _t("3 columns"),
                description: _t("Convert into 3 columns"),
                categoryId: "structure",
                isAvailable: columnIsAvailable(3),
                commandId: "columnize",
                commandParams: { numberOfColumns: 3 },
            },
            {
                title: _t("4 columns"),
                description: _t("Convert into 4 columns"),
                categoryId: "structure",
                isAvailable: columnIsAvailable(4),
                commandId: "columnize",
                commandParams: { numberOfColumns: 4 },
            },
            {
                title: _t("Remove columns"),
                description: _t("Back to one column"),
                categoryId: "structure",
                isAvailable: (selection) =>
                    !!closestElement(selection.anchorNode, ".o_text_columns .row"),
                commandId: "columnize",
                commandParams: { numberOfColumns: 0 },
            },
        ],
        hints: [
            {
                selector: `.odoo-editor-editable .o_text_columns div[class^='col-'],
                            .odoo-editor-editable .o_text_columns div[class^='col-']>p:first-child`,
                text: _t("Empty column"),
            },
        ],
        unremovable_node_predicates: isUnremovableColumn,
        power_buttons_visibility_predicates: ({ anchorNode }) =>
            !closestElement(anchorNode, ".o_text_columns"),
    };

    columnize({ numberOfColumns, addParagraphAfter = true } = {}) {
        const selectionToRestore = this.dependencies.selection.getEditableSelection();
        const anchor = selectionToRestore.anchorNode;
        const hasColumns = !!closestElement(anchor, ".o_text_columns");
        if (hasColumns) {
            if (numberOfColumns) {
                this.changeColumnsNumber(anchor, numberOfColumns);
            } else {
                this.removeColumns(anchor);
            }
        } else if (numberOfColumns) {
            this.createColumns(anchor, numberOfColumns, addParagraphAfter);
        }
        this.dependencies.selection.setSelection(selectionToRestore);
        this.dependencies.history.addStep();
    }

    removeColumns(anchor) {
        const container = closestElement(anchor, ".o_text_columns");
        const rows = unwrapContents(container);
        for (const row of rows) {
            const columns = unwrapContents(row);
            for (const column of columns) {
                unwrapContents(column);
                // const columnContents = unwrapContents(column);
                // for (const node of columnContents) {
                //     resetOuids(node);
                // }
            }
        }
    }

    createColumns(anchor, numberOfColumns, addParagraphAfter) {
        const container = this.document.createElement("div");
        if (!closestElement(anchor, ".container")) {
            container.classList.add("container");
        }
        container.classList.add("o_text_columns");
        const row = this.document.createElement("div");
        row.classList.add("row");
        container.append(row);
        const block = closestBlock(anchor);
        // resetOuids(block);
        const columnSize = Math.floor(12 / numberOfColumns);
        const columns = [];
        for (let i = 0; i < numberOfColumns; i++) {
            const column = this.document.createElement("div");
            column.classList.add(`col-${columnSize}`);
            row.append(column);
            columns.push(column);
        }
        block.before(container);
        columns.shift().append(block);
        for (const column of columns) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(this.document.createElement("br"));
            column.append(baseContainer);
        }
        if (addParagraphAfter) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(this.document.createElement("br"));
            container.after(baseContainer);
        }
    }

    changeColumnsNumber(anchor, numberOfColumns) {
        const row = closestElement(anchor, ".row");
        const columns = [...row.children];
        const columnSize = Math.floor(12 / numberOfColumns);
        const diff = numberOfColumns - columns.length;
        if (!diff) {
            return;
        }
        for (const column of columns) {
            column.className = column.className.replace(
                REGEX_BOOTSTRAP_COLUMN,
                `col$1-${columnSize}`
            );
        }
        if (diff > 0) {
            // Add extra columns.
            let lastColumn = columns[columns.length - 1];
            for (let i = 0; i < diff; i++) {
                const column = this.document.createElement("div");
                column.classList.add(`col-${columnSize}`);
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                baseContainer.append(this.document.createElement("br"));
                column.append(baseContainer);
                lastColumn.after(column);
                lastColumn = column;
            }
        } else if (diff < 0) {
            // Remove superfluous columns.
            const contents = [];
            for (let i = diff; i < 0; i++) {
                const column = columns.pop();
                const columnContents = unwrapContents(column);
                // for (const node of columnContents) {
                //     resetOuids(node);
                // }
                contents.unshift(...columnContents);
            }
            columns[columns.length - 1].append(...contents);
        }
    }
}
