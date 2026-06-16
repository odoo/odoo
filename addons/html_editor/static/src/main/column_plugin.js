import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { closestElement, firstLeaf } from "@html_editor/utils/dom_traversal";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { nodeSize } from "@html_editor/utils/position";

const REGEX_BOOTSTRAP_COLUMN = /(^| )col(-[a-zA-Z]+)?(-\d+)?(?= |$)/;

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
        return row
            ? row.childElementCount !== numberOfColumns
            : closestBlock(selection.anchorNode)?.parentNode?.isContentEditable;
    };
}

export class ColumnPlugin extends Plugin {
    static id = "column";
    static dependencies = ["baseContainer", "selection", "history", "dom"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "columnize",
                title: _t("Columnize"),
                description: _t("Convert into columns"),
                icon: "fa-columns",
                run: this.columnize.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: [
            {
                title: _t("2 columns"),
                description: _t("Convert into 2 columns"),
                categoryId: "structure",
                isAvailable: columnIsAvailable(2),
                commandId: "columnize",
                commandParams: 2,
            },
            {
                title: _t("3 columns"),
                description: _t("Convert into 3 columns"),
                categoryId: "structure",
                isAvailable: columnIsAvailable(3),
                commandId: "columnize",
                commandParams: 3,
            },
            {
                title: _t("4 columns"),
                description: _t("Convert into 4 columns"),
                categoryId: "structure",
                isAvailable: columnIsAvailable(4),
                commandId: "columnize",
                commandParams: 4,
            },
            {
                title: _t("Remove column layout"),
                description: _t("Convert columns to regular content"),
                categoryId: "structure",
                isAvailable: (selection) =>
                    !!closestElement(selection.anchorNode, ".o_text_columns .row"),
                commandId: "columnize",
                commandParams: 0,
            },
        ],
        hints: [
            {
                selector: `.odoo-editor-editable .o_text_columns div[class*='col-'],
                            .odoo-editor-editable .o_text_columns div[class*='col-']>${baseContainerGlobalSelector}:first-child`,
                text: _t("Empty column"),
            },
        ],
        unremovable_node_predicates: isUnremovableColumn,
        power_buttons_visibility_predicates: ({ anchorNode }) =>
            !closestElement(anchorNode, ".o_text_columns"),
        move_node_whitelist_selectors: ".o_text_columns",
        move_node_blacklist_selectors: ".o_text_columns *",
        hint_targets_providers: (selectionData) => {
            if (!selectionData.documentSelection) {
                return [];
            }
            const anchorNode = selectionData.documentSelection.anchorNode;
            const columnContainer = closestElement(anchorNode, "div.o_text_columns");
            if (!columnContainer) {
                return [];
            }
            const closestColumn = closestElement(anchorNode, "div[class*='col-']");
            const closestBlockEl = closestBlock(anchorNode);
            return [...columnContainer.querySelectorAll("div[class*='col-']")]
                .map((column) => {
                    const block = closestBlock(firstLeaf(column));
                    return column === closestColumn && block !== closestBlockEl ? null : block;
                })
                .filter(Boolean);
        },
    };

    /**
     * Returns whether the column has valid content (i.e. not just empty blocks).
     *
     * @param {HTMLElement} column
     * @returns {boolean}
     */
    hasValidContent(column) {
        return ![...column.children].every((node) => isEmptyBlock(node));
    }

    columnize(numberOfColumns) {
        const cursors = this.dependencies.selection.preserveSelection();
        const anchor = cursors.anchor.node;
        const hasColumns = !!closestElement(anchor, ".o_text_columns");
        let cursorFallbackNode;

        if (hasColumns) {
            if (numberOfColumns) {
                const column = this.changeColumnsNumber(anchor, numberOfColumns);
                cursorFallbackNode = column?.lastChild;
            } else {
                const remainingContent = this.removeColumns(anchor);
                cursorFallbackNode = remainingContent.at(-1);
            }
        } else if (numberOfColumns) {
            const li = closestElement(anchor, "li");
            if (li) {
                this.createColumnsFromList(anchor, li, numberOfColumns);
                return;
            }
            this.createColumns(anchor, numberOfColumns);
        }

        if (!anchor.isConnected) {
            cursors.remapNode(anchor, cursorFallbackNode);
            cursors.setOffset(cursorFallbackNode, nodeSize(cursorFallbackNode));
        }

        cursors.restore();
        this.dependencies.history.addStep();
    }

    createColumnsFromList(anchor, li, numberOfColumns) {
        const currentList = li.closest("ol, ul");
        let listBeforeBlock = currentList;
        if (li.nextElementSibling) {
            const nextLi = li.nextElementSibling;
            const newList = currentList.cloneNode(false);
            nextLi.parentNode.after(newList);
            while (nextLi.nextSibling) {
                newList.append(nextLi.nextSibling);
            }
            newList.prepend(nextLi);
            listBeforeBlock = newList.previousElementSibling;
        }

        const { container, columns } = this.buildColumnsContainer(anchor, numberOfColumns);
        for (const column of columns) {
            column.append(this.createEmptyParagraph());
        }
        listBeforeBlock.after(this.createEmptyParagraph());

        this.dependencies.selection.setSelection({
            anchorNode: listBeforeBlock.nextElementSibling,
            anchorOffset: 0,
        });
        this.dependencies.dom.insert(container);
        this.dependencies.selection.setSelection({
            anchorNode: columns[0].firstElementChild,
            anchorOffset: 0,
        });
        this.dependencies.history.addStep();
    }

    /**
     * @param {HTMLElement} anchor
     * @returns {HTMLElement[]}
     */
    removeColumns(anchor) {
        const container = closestElement(anchor, ".o_text_columns");
        const contents = [];

        for (const row of [...container.childNodes]) {
            for (const column of [...row.childNodes]) {
                if (this.hasValidContent(column)) {
                    contents.push(...column.children);
                }
            }
        }

        if (!contents.length) {
            contents.push(this.createEmptyParagraph());
        }
        container.replaceWith(...contents);
        return contents;
    }

    createColumns(anchor, numberOfColumns, addParagraphAfter) {
        const { container, columns } = this.buildColumnsContainer(anchor, numberOfColumns);
        const block = closestBlock(anchor);
        columns.shift().append(block);
        for (const column of columns) {
            column.append(this.createEmptyParagraph());
        }
        this.dependencies.dom.insert(container);
    }

    buildColumnsContainer(anchor, numberOfColumns) {
        const container = this.document.createElement("div");
        if (!closestElement(anchor, ".container")) {
            container.classList.add("container");
        }
        container.classList.add("o_text_columns", "o-contenteditable-false");
        const row = this.document.createElement("div");
        row.classList.add("row");
        container.append(row);
        const columnSize = Math.floor(12 / numberOfColumns);
        const columns = [];
        for (let i = 0; i < numberOfColumns; i++) {
            const column = this.document.createElement("div");
            column.classList.add(`col-${columnSize}`, "o-contenteditable-true");
            row.append(column);
            columns.push(column);
        }
        return { container, columns };
    }

    createEmptyParagraph() {
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        baseContainer.append(this.document.createElement("br"));
        return baseContainer;
    }

    /**
     * @param {HTMLElement} anchor
     * @param {number} numberOfColumns
     * @returns {HTMLElement | undefined} If the column is getting removed, undefined if not.
     */
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
                `$1col$2-${columnSize}`
            );
        }
        if (diff > 0) {
            // Add extra columns.
            let lastColumn = columns[columns.length - 1];
            for (let i = 0; i < diff; i++) {
                const column = this.document.createElement("div");
                column.classList.add(`col-${columnSize}`, "o-contenteditable-true");
                column.append(this.createEmptyParagraph());
                lastColumn.after(column);
                lastColumn = column;
            }
        } else if (diff < 0) {
            // Remove superfluous columns.
            const contents = [];
            for (let i = diff; i < 0; i++) {
                const column = columns.pop();
                if (this.hasValidContent(column)) {
                    contents.unshift(...column.children);
                }
                column.remove();
            }
            const targetColumn = columns[columns.length - 1];
            targetColumn.append(...contents);
            return targetColumn;
        }
    }
}
