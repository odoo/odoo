/** @odoo-module **/

import { PivotGroupByMenu } from "@web/views/pivot/pivot_group_by_menu";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import fieldUtils from "web.field_utils";

const { Component } = owl;
const formatterRegistry = registry.category("formatters");

export class PivotRenderer extends Component {
    setup() {
        this.model = this.props.model;
        this.table = this.model.getTable();
        this.l10n = localization;
    }
    willUpdateProps() {
        this.table = this.model.getTable();
    }
    /**
     * Get the formatted value of the cell.
     *
     * @private
     * @param {Object} cell
     * @returns {string} Formatted value
     */
    getFormattedValue(cell) {
        const field = this.model.metaData.measures[cell.measure];
        let formatType = this.model.metaData.widgets[cell.measure];
        if (!formatType) {
            const fieldType = field.type;
            formatType = fieldType === "many2one" ? "integer" : fieldType;
        }
        //If the formatter is not found on the registry, search on the legacy fieldUtils.format.
        //This must be removed when all the formatters will be on the registry
        const formatter = formatterRegistry.get(formatType, null) || fieldUtils.format[formatType];
        if (!formatter) {
            throw new Error(`${formatType} is not a defined formatter!`);
        }
        return formatter(cell.value, field);
    }
    /**
     * Get the formatted variation of a cell.
     *
     * @private
     * @param {Object} cell
     * @returns {string} Formatted variation
     */
    getFormattedVariation(cell) {
        if (isNaN(cell.value)) {
            return "-";
        }
        const formatPercentage = formatterRegistry.get("percentage");
        return formatPercentage(cell.value, this.model.metaData.fields[cell.measure]);
    }
    /**
     * Retrieve the padding of a left header.
     *
     * @param {Object} cell
     * @returns {Number} Padding
     */
    getPadding(cell) {
        return 5 + cell.indent * 30;
    }

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    onCellClicked(cell) {
        this.props.onCellClicked(cell);
    }
    /**
     * Handle the adding of a custom groupby (inside the view, not the searchview).
     *
     * @param {"col"|"row"} type
     * @param {CustomEvent} ev
     */
    onAddCustomGroupBy(type, ev) {
        this.model.addGroupBy({ ...ev.detail, custom: true, type });
    }

    /**
     * Handle the selection of a groupby dropdown item.
     *
     * @param {"col"|"row"} type
     * @param {CustomEvent} ev
     */
    onDropdownItemSelected(type, ev) {
        this.model.addGroupBy({ ...ev.detail.payload, type });
    }
    /**
     * Handle a click on a header cell.
     *
     * @param {Object} cell
     * @param {string} type col or row
     */
    onHeaderClick(cell, type) {
        if (cell.isLeaf && cell.isFolded) {
            this.model.expandGroup(cell.groupId, type);
        } else if (!cell.isLeaf) {
            this.model.closeGroup(cell.groupId, type);
        }
    }
    /**
     * Handle a click on a measure cell.
     *
     * @param {Object} cell
     */
    onMeasureClick(cell) {
        this.model.sortRows({
            groupId: cell.groupId,
            measure: cell.measure,
            order: (cell.order || "desc") === "asc" ? "desc" : "asc",
            originIndexes: cell.originIndexes,
        });
    }
    /**
     * Hover the column in which the mouse is.
     *
     * @param {MouseEvent} ev
     */
    onMouseEnter(ev) {
        var index = [...ev.currentTarget.parentNode.children].indexOf(ev.currentTarget);
        if (ev.currentTarget.tagName === "TH") {
            if (
                !ev.currentTarget.classList.contains("o_pivot_origin_row") &&
                this.model.metaData.origins.length === 2
            ) {
                index = 3 * index; // two origins + comparison column
            }
            index += 1; // row groupbys column
        }
        this.el
            .querySelectorAll("td:nth-child(" + (index + 1) + ")")
            .forEach((elt) => elt.classList.add("o_cell_hover"));
    }
    /**
     * Remove the hover on the columns.
     */
    onMouseLeave() {
        this.el
            .querySelectorAll(".o_cell_hover")
            .forEach((elt) => elt.classList.remove("o_cell_hover"));
    }
}
PivotRenderer.template = "web.PivotRenderer";
PivotRenderer.components = { PivotGroupByMenu };
PivotRenderer.props = ["model", "onCellClicked"];
