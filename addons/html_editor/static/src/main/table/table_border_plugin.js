import { proxy } from "@odoo/owl";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { getCSSVariableValue, getHtmlStyle, removeStyle } from "@html_editor/utils/formatting";
import { READ, withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { normalizeCSSColor } from "@web/core/utils/colors";
import { ColorSelector } from "@html_editor/main/font/color_selector";
import { TableBorderStyleSelector } from "./table_border_style_selector";
import { TableBorderWidthSelector } from "./table_border_width_selector";
import { isTableCell } from "@html_editor/utils/dom_info";

const borderStyleItems = [
    {
        value: "solid",
    },
    {
        value: "dashed",
    },
    {
        value: "dotted",
    },
    {
        value: "double",
    },
];

const borderWidthItems = [
    {
        value: "1px",
        margin: "5px",
    },
    {
        value: "2px",
        margin: "6px",
    },
    {
        value: "3px",
        margin: "6px",
    },
    {
        value: "4px",
        margin: "7px",
    },
    {
        value: "5px",
        margin: "7px",
    },
];

export class TableBorderPlugin extends Plugin {
    static id = "tableBorder";
    static dependencies = ["colorUi", "history", "selection"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        toolbar_groups: withSequence(25, { id: "table_border", namespaces: ["expanded", "table"] }),
        toolbar_items: [
            withSequence(10, {
                id: "table_border_color",
                groupId: "table_border",
                namespaces: ["expanded", "table"],
                description: _t("Table border color"),
                isAvailable: () =>
                    this.dependencies.selection
                        .getTargetedNodes()
                        .some((node) => closestElement(node, isTableCell)),
                Component: ColorSelector,
                props: {
                    ...this.dependencies.colorUi.getPropsForColorSelector("foreground"),
                    type: "custom",
                    customIcon: "edit",
                    enabledTabs: ["solid", "custom"],
                    colorPrefix: "--",
                    getSelectedColors: () => {
                        const borderColor =
                            this.getTableSelectedBorder("color", "default") || "transparent";
                        if (borderColor === "default") {
                            // Do not specify selection and display solid tab.
                            this.selectedBorderColors.color = "";
                        } else {
                            this.selectedBorderColors.color = borderColor;
                        }
                        return this.selectedBorderColors;
                    },
                    applyColor: (color) => this.applyBorderCommit("color", color),
                    applyColorPreview: (color) => this.applyBorderPreview("color", color),
                    applyColorResetPreview: this.applyBorderResetPreview.bind(this),
                    onClose: () => this.dependencies.selection.focusEditable(),
                    getTargetedElements: () => {
                        const nodes = this.dependencies.selection.getTargetedNodes();
                        return nodes.map((node) => closestElement(node, "table"));
                    },
                    getDefaultColor: () => "var(--gray-300)",
                },
            }),
            withSequence(11, {
                id: "table_border_width",
                groupId: "table_border",
                namespaces: ["expanded", "table"],
                description: _t("Table border width"),
                isAvailable: () =>
                    this.dependencies.selection
                        .getTargetedNodes()
                        .some((node) => closestElement(node, isTableCell)),
                Component: TableBorderWidthSelector,
                props: {
                    getItems: () => borderWidthItems,
                    getDisplay: () => {
                        this.selectedBorderWidth.displayName = this.getTableSelectedBorder("width");
                        return this.selectedBorderWidth;
                    },
                    previewable: () => this.previewableSetBorderWidth,
                },
            }),
            withSequence(12, {
                id: "table_border_style",
                groupId: "table_border",
                namespaces: ["expanded", "table"],
                description: _t("Table border style"),
                isAvailable: () =>
                    this.dependencies.selection
                        .getTargetedNodes()
                        .some((node) => closestElement(node, isTableCell)),
                Component: TableBorderStyleSelector,
                props: {
                    getItems: () => borderStyleItems,
                    getDisplay: () => {
                        this.selectedBorderStyle.displayName = this.getTableSelectedBorder("style");
                        return this.selectedBorderStyle;
                    },
                    previewable: () => this.previewableSetBorderStyle,
                },
            }),
        ],

        /** Handlers */
        on_selectionchange_handlers: withSequence(READ, this.updateTableBorderParams.bind(this)),
        on_history_commit_undone_handlers: this.updateTableBorderParams.bind(this),
        on_history_commit_redone_handlers: this.updateTableBorderParams.bind(this),
        on_savepoint_restored_handlers: this.updateTableBorderParams.bind(this),
    };

    setup() {
        // Background color is required by the color picker.
        this.selectedBorderColors = proxy({ color: "", backgroundColor: "" });
        this.selectedBorderWidth = proxy({ displayName: "1px" });
        this.selectedBorderStyle = proxy({ displayName: "solid" });
        this.previewableApplyBorder = this.dependencies.history.makePreviewableOperation(
            (prop, value) => this.applyBorder(prop, value)
        );
        this.previewableSetBorderWidth = this.dependencies.history.makePreviewableOperation(
            (item) => {
                this.applyBorder("width", item.value);
                this.updateTableBorderParams();
            }
        );
        this.previewableSetBorderStyle = this.dependencies.history.makePreviewableOperation(
            (item) => {
                this.applyBorder("style", item.value);
                this.updateTableBorderParams();
            }
        );
    }

    updateTableBorderParams() {
        this.selectedBorderWidth.displayName = this.getTableSelectedBorder("width");
        this.selectedBorderStyle.displayName = this.getTableSelectedBorder("style");
        this.selectedBorderColors.color =
            this.getTableSelectedBorder("color", "default") || "transparent";
    }

    /**
     * Returns the current value of a border property for a cell.
     *
     * @param {HTMLTableCellElement} cell
     * @param {string} subProperty color, width or style
     * @param {string} [defaultReplacement] value to return instead of default value
     * @returns {string} property value
     */
    getCellBorder(cell, subProperty, defaultReplacement) {
        const property = `border-${subProperty}`;
        if (defaultReplacement && !cell.style.getPropertyValue(property)) {
            return defaultReplacement;
        }
        const cellStyle = getComputedStyle(cell);
        let result = cellStyle.getPropertyValue(property);
        // Handle defaults
        switch (subProperty) {
            case "style":
                if (result === "inset") {
                    result = "solid";
                }
                break;
            case "width":
                if (result === "0px" || result.includes(" ")) {
                    result = "1px";
                }
                break;
        }
        return result;
    }
    /**
     * Returns the current value of a border property for selected cells inside the selected table.
     *
     * @param {string} subProperty color, width or style
     * @param {string} [defaultReplacement] value to return instead of default value
     * @returns {string} property value
     */
    getTableSelectedBorder(subProperty, defaultReplacement) {
        const cells = [
            ...new Set(
                this.dependencies.selection
                    .getTargetedNodes()
                    .map((node) => closestElement(node, isTableCell))
                    .filter(Boolean)
            ),
        ];
        let value;
        for (const cell of cells) {
            const cellValue = this.getCellBorder(cell, subProperty, defaultReplacement);
            if (value && cellValue !== value) {
                return undefined;
            }
            value = cellValue;
        }
        if (subProperty === "color") {
            value = normalizeCSSColor(value);
        }
        return value;
    }

    /**
     * Applies a border property value on tables of the current selection.
     *
     * @param {string} subProperty color, width or style
     * @param {string} value
     */
    applyBorder(subProperty, value) {
        const cells = [
            ...new Set(
                this.dependencies.selection
                    .getTargetedNodes()
                    .map((node) => closestElement(node, isTableCell))
                    .filter(Boolean)
            ),
        ];
        if (value === "") {
            for (const cell of cells) {
                removeStyle(cell, `border-${subProperty}`);
            }
            return;
        }
        if (subProperty === "color" && value.startsWith("--")) {
            const htmlStyle = getHtmlStyle(this.document);
            value = getCSSVariableValue(value.substring(2), htmlStyle);
        }
        const tables = new Set();
        for (const cell of cells) {
            const property = `border-${subProperty}`;
            if (!cell.style.getPropertyValue(property)) {
                // Copy defaults.
                for (const prop of ["color", "width", "style"]) {
                    cell.style.setProperty(`border-${prop}`, this.getCellBorder(cell, prop));
                }
            }
            cell.style.setProperty(property, value);
            if (property === "border-style" && value === "double") {
                // Set a minimum of 3px by default
                if (parseInt(cell.style.getPropertyValue("border-width")) < 3) {
                    cell.style.setProperty("border-width", "3px");
                }
            }
            const table = closestElement(cell, "table");
            if (table) {
                tables.add(table);
            }
        }
        for (const table of tables) {
            table.classList.add("o-table-cellbordered");
        }
    }

    /**
     * Apply border on the current selected tables.
     *
     * @param {string} subProperty color, width or style
     * @param {string} value
     */
    applyBorderCommit(subProperty, value) {
        this.previewableApplyBorder.commit(subProperty, value);
        if (subProperty === "color") {
            if (value.startsWith("--")) {
                const htmlStyle = getHtmlStyle(this.document);
                value = getCSSVariableValue(value.substring(2), htmlStyle);
            }
            this.selectedBorderColors.color = value;
        }
    }
    /**
     * Apply border on the current selected tables in preview mode so that it can be reset.
     *
     * @param {string} subProperty color, width or style
     * @param {string} value
     */
    applyBorderPreview(subProperty, value) {
        // Preview the border before applying it.
        this.previewableApplyBorder.preview(subProperty, value, true);
    }
    /**
     * Reset the border applied in preview mode.
     */
    applyBorderResetPreview() {
        this.previewableApplyBorder.revert();
    }
}
