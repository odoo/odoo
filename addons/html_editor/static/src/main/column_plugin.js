import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { unwrapContents } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";

const REGEX_BOOTSTRAP_COLUMN = /(?:^| )col(-[a-zA-Z]+)?(-\d+)?(?:$| )/;

function isUnremovableColumn(element, root) {
    const isColumnInnerStructure =
        element.tagName === "DIV" &&
        [...element.classList].some((cls) => /^row$|^col$|^col-/.test(cls));

    if (!isColumnInnerStructure) {
        return false;
    }
    if (!root) {
        return true;
    }
    const closestColumnContainer = closestElement(element, "div.o_text_columns");
    return !root.contains(closestColumnContainer);
}

function columnisAvailable(numberOfColumns) {
    return (node) => {
        const row = closestElement(node, ".o_text_columns .row");
        return row && row.childElementCount === numberOfColumns;
    };
}

export class ColumnPlugin extends Plugin {
    static name = "column";
    static dependencies = ["selection"];
    resources = {
        isUnremovable: isUnremovableColumn,
        powerboxItems: [
            {
                name: _t("2 columns"),
                description: _t("Convert into 2 columns"),
                category: "structure",
                fontawesome: "fa-columns",
                isAvailable: columnisAvailable(2),
                action(dispatch) {
                    dispatch("COLUMNIZE", { numberOfColumns: 2 });
                },
            },
            {
                name: _t("3 columns"),
                description: _t("Convert into 3 columns"),
                category: "structure",
                fontawesome: "fa-columns",
                isAvailable: columnisAvailable(3),
                action(dispatch) {
                    dispatch("COLUMNIZE", { numberOfColumns: 3 });
                },
            },
            {
                name: _t("4 columns"),
                description: _t("Convert into 4 columns"),
                category: "structure",
                fontawesome: "fa-columns",
                isAvailable: columnisAvailable(4),
                action(dispatch) {
                    dispatch("COLUMNIZE", { numberOfColumns: 4 });
                },
            },
            {
                name: _t("Remove columns"),
                description: _t("Back to one column"),
                category: "structure",
                fontawesome: "fa-columns",
                isAvailable(node) {
                    const row = closestElement(node, ".o_text_columns .row");
                    return !row;
                },
                action(dispatch) {
                    dispatch("COLUMNIZE", { numberOfColumns: 0 });
                },
            },
        ],
        hints: [
            {
                selector: `.odoo-editor-editable .o_text_columns div[class^='col-'],
                            .odoo-editor-editable .o_text_columns div[class^='col-']>p:first-child`,
                text: _t("Empty column"),
            },
        ],
        showPowerButtons: (selection) => !closestElement(selection.anchorNode, ".o_text_columns"),
    };

    handleCommand(command, payload) {
        switch (command) {
            case "COLUMNIZE": {
                const { numberOfColumns, addParagraphAfter } = payload;
                this.columnize(numberOfColumns, addParagraphAfter);
                this.dispatch("ADD_STEP");
                break;
            }
        }
    }
    columnize(numberOfColumns, addParagraphAfter = true) {
        const selectionToRestore = this.shared.getEditableSelection();
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
        this.shared.setSelection(selectionToRestore);
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
            const p = this.document.createElement("p");
            p.append(this.document.createElement("br"));
            column.append(p);
        }
        if (addParagraphAfter) {
            const p = this.document.createElement("p");
            p.append(this.document.createElement("br"));
            container.after(p);
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
                const p = this.document.createElement("p");
                p.append(this.document.createElement("br"));
                column.append(p);
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
