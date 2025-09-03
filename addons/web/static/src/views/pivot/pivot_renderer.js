import { Component, onWillUpdateProps, useRef } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { sortBy } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";
import { CustomGroupByItem } from "@web/search/custom_group_by_item/custom_group_by_item";
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";
import { getIntervalOptions } from "@web/search/utils/dates";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import { MultiCurrencyPopover } from "@web/views/view_components/multi_currency_popover";
import { ReportViewMeasures } from "@web/views/view_components/report_view_measures";

const formatters = registry.category("formatters");

class PivotDropdown extends Dropdown {
    /**
     * @override
     */
    get position() {
        return this.props.state.position || "bottom-start";
    }
    /**
     * @override
     */
    get target() {
        return this.props.state.target;
    }
}

export class PivotRenderer extends Component {
    static template = "web.PivotRenderer";
    static components = {
        CheckBox,
        CustomGroupByItem,
        Dropdown,
        DropdownItem,
        PivotDropdown,
        PropertiesGroupByItem,
        ReportViewMeasures,
    };
    static props = ["model", "buttonTemplate"];

    setup() {
        this.actionService = useService("action");
        this.model = this.props.model;
        this.table = this.model.getTable();
        this.l10n = localization;
        this.tableRef = useRef("table");

        this.dropdown = {
            state: new DropdownState({
                onClose: () => {
                    delete this.dropdown.cellInfo;
                    delete this.dropdown.state.target;
                    delete this.dropdown.state.position;
                },
            }),
        };
        this.multiCurrencyPopover = usePopover(MultiCurrencyPopover, {
            position: "right",
        });
        const fields = [];
        for (const [fieldName, field] of Object.entries(this.env.searchModel.searchViewFields)) {
            if (this.validateField(fieldName, field)) {
                fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields = sortBy(fields, "string");

        onWillUpdateProps(this.onWillUpdateProps);
    }
    onWillUpdateProps() {
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
        const fieldAttrs = this.model.metaData.fieldAttrs[cell.measure] ?? {};
        const fieldInfo = {
            options: fieldAttrs.options ?? {},
            attrs: fieldAttrs,
        };
        let formatType = this.model.metaData.widgets[cell.measure];
        if (!formatType) {
            const fieldType = field.type;
            formatType = ["many2one", "reference"].includes(fieldType) ? "integer" : fieldType;
        }
        const formatter = formatters.get(formatType);
        const formatOptions = { field };
        if (formatter.extractOptions) {
            Object.assign(formatOptions, formatter.extractOptions(fieldInfo));
        }
        if (formatType === "monetary") {
            if (cell.currencyIds.length > 1) {
                formatOptions.currencyId = user.activeCompany.currency_id;
                return {
                    rawValue: cell.value,
                    value: formatter(cell.value, formatOptions),
                    currencies: cell.currencyIds,
                };
            }
            formatOptions.currencyId = cell.currencyIds[0];
        }
        return { value: formatter(cell.value, formatOptions) };
    }

    /**
     * @returns {Object[]}
     */
    get groupByItems() {
        let items = this.env.searchModel.getSearchItems(
            (searchItem) =>
                ["groupBy", "dateGroupBy"].includes(searchItem.type) && !searchItem.custom
        );
        if (items.length === 0) {
            items = this.fields;
        }

        // Add custom groupbys
        let groupNumber = 1 + Math.max(0, ...items.map(({ groupNumber: n }) => n || 0));
        for (const [fieldName, customGroupBy] of this.model.metaData.customGroupBys.entries()) {
            items.push({ ...customGroupBy, name: fieldName, groupNumber: groupNumber++ });
        }

        return items.map((item) => ({
            ...item,
            id: item.id || item.name,
            fieldName: item.fieldName || item.name,
            description: item.description || item.string,
            options:
                item.options ||
                (["date", "datetime"].includes(item.type) ? getIntervalOptions() : undefined),
        }));
    }

    /**
     * @returns {boolean}
     */
    get hideCustomGroupBy() {
        return this.env.searchModel.hideCustomGroupBy || false;
    }

    /**
     * @param {string} fieldName
     * @param {Object} field
     * @returns {boolean}
     */
    validateField(fieldName, field) {
        const { groupable, type } = field;
        return groupable && fieldName !== "id" && GROUPABLE_TYPES.includes(type);
    }

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Handle the adding of a custom groupby (inside the view, not the searchview).
     *
     * @param {string} fieldName
     */
    onAddCustomGroupBy(fieldName) {
        this.model.addGroupBy({ ...this.dropdown.cellInfo, fieldName, custom: true });
        this.dropdown.state.close();
    }

    /**
     * Handle the selection of a groupby dropdown item.
     *
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onGroupBySelected({ itemId, optionId }) {
        const { fieldName } = this.groupByItems.find(({ id }) => id === itemId);
        this.model.addGroupBy({ ...this.dropdown.cellInfo, fieldName, interval: optionId });
    }
    /**
     * Handle a click on a header cell.
     *
     * @param {PointerEvent} ev
     * @param {Object} cell
     * @param {boolean} isXAxis
     */
    onHeaderClick(ev, cell, isXAxis) {
        const type = isXAxis ? "col" : "row";
        if (cell.isLeaf && !cell.isFolded) {
            if (this.dropdown.state.isOpen) {
                this.dropdown.state.close();
            } else {
                this.dropdown.cellInfo = { type, groupId: cell.groupId };
                Object.assign(this.dropdown.state, {
                    target: ev.target.closest(".o_pivot_header_cell_closed"),
                    position: isXAxis ? "bottom-start" : "bottom-end",
                    isOpen: true,
                });
            }
        } else if (cell.isLeaf && cell.isFolded) {
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
            index += 1; // row groupbys column
        }
        this.tableRef.el
            .querySelectorAll("td:nth-child(" + (index + 1) + ")")
            .forEach((elt) => elt.classList.add("o_cell_hover"));
    }
    /**
     * Remove the hover on the columns.
     */
    onMouseLeave() {
        this.tableRef.el
            .querySelectorAll(".o_cell_hover")
            .forEach((elt) => elt.classList.remove("o_cell_hover"));
    }

    /**
     * Exports the current pivot table data in a xls file. For this, we have to
     * serialize the current state, then call the server /web/pivot/export_xlsx.
     * Force a reload before exporting to ensure to export up-to-date data.
     */
    onDownloadButtonClicked() {
        if (this.model.getTableWidth() > 16384) {
            throw new Error(
                _t(
                    "For Excel compatibility, data cannot be exported if there are more than 16384 columns.\n\nTip: try to flip axis, filter further or reduce the number of measures."
                )
            );
        }
        const table = this.model.exportData();
        download({
            url: "/web/pivot/export_xlsx",
            data: { data: new Blob([JSON.stringify(table)], { type: "application/json" }) },
        });
    }
    /**
     * Expands all groups
     */
    onExpandButtonClicked() {
        this.model.expandAll();
    }
    /**
     * Flips axis
     */
    onFlipButtonClicked() {
        this.model.flip();
    }
    /**
     * Toggles the given measure
     *
     * @param {Object} param0
     * @param {string} param0.measure
     */
    onMeasureSelected({ measure }) {
        this.model.toggleMeasure(measure);
    }
    openMultiCurrencyPopover(ev, value, currencyIds) {
        if (!this.multiCurrencyPopover.isOpen) {
            this.multiCurrencyPopover.open(ev.target, {
                currencyIds,
                target: ev.target,
                value,
            });
        }
    }
    /**
     * Execute the action to open the view on the current model.
     *
     * @param {Array} domain
     * @param {Array} views
     * @param {Object} context
     */
    openView(domain, views, context, newWindow) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: this.model.metaData.title,
                res_model: this.model.metaData.resModel,
                views: views,
                view_mode: "list",
                target: "current",
                context,
                domain,
            },
            {
                newWindow,
            }
        );
    }
    /**
     * @param {CustomEvent} ev
     */
    onOpenView(cell, newWindow) {
        if (cell.value === undefined || this.model.metaData.disableLinking) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        Object.keys(context).forEach((x) => {
            if (x === "group_by" || x.startsWith("search_default_")) {
                delete context[x];
            }
        });

        // retrieve form and list view ids from the action
        const { views = [] } = this.env.config;
        this.views = ["list", "form"].map((viewType) => {
            const view = views.find((view) => view[1] === viewType);
            return [view ? view[0] : false, viewType];
        });

        const group = { rowValues: cell.groupId[0], colValues: cell.groupId[1] };
        this.openView(this.model.getGroupDomain(group), this.views, context, newWindow);
    }
}
