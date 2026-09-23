// @ts-check
/** @odoo-module native */

import { Component, onPatched, useRef } from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownState } from "@web/components/dropdown/dropdown_hook";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useAction } from "@web/core/action_port";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { getFieldCodec } from "@web/core/field_codec";
import { localization } from "@web/core/l10n/localization";
import { download } from "@web/core/network/download";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useRenderCounter } from "@web/core/utils/render_instrumentation";
import { useReactiveModel } from "@web/model/model";
import { CustomGroupByItem } from "@web/search/custom_group_by_item/custom_group_by_item";
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";
import { getIntervalOptions } from "@web/search/utils/dates";
import { groupableFields, isGroupableField } from "@web/search/utils/misc";
import { usePopover } from "@web/ui/popover/popover_hook";
import { MultiCurrencyPopover } from "@web/views/view_components/multi_currency_popover";
import { ReportViewMeasures } from "@web/views/view_components/report_view_measures";
import {
    drillDownContext,
    drillDownViews,
    openDrillDownView,
} from "@web/views/view_utils";

class PivotDropdown extends Dropdown {
    /** @override */
    get position() {
        return this.props.state.position || "bottom-start";
    }
    /** @override */
    get target() {
        return this.props.state.target;
    }
}

const log = makeLogger("web.view.pivot");

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
        useRenderCounter("pivot.PivotRenderer");
        useLifecycleLog(log);
        this.actionService = useAction();
        this.notification = useService("notification");
        this.model = useReactiveModel(this.props.model);
        this.columnCellsCache = new Map();
        this.hoveredCells = null;
        /** @type {{ epoch?: number, table?: any }} */
        this.tableMemo = {};
        onPatched(() => {
            this.columnCellsCache.clear();
            this.hoveredCells = null;
        });
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
        this.fields = groupableFields(
            this.env.searchModel.searchViewFields,
            (name, field) => this.isGroupableField(name, field),
        );
    }
    /** @private */
    computeMeasureFormatters() {
        const { fieldAttrs, measures, widgets, activeMeasures } = this.model.metaData;
        /** @type {Map<string, { codec: any, formatType: string, baseOptions: Record<string, any> }>} */
        this.measureFormatters = new Map();
        for (const measure of activeMeasures) {
            const field = measures[measure];
            const attrs = fieldAttrs[measure] ?? {};
            const fieldInfo = {
                options: attrs.options ?? {},
                attrs,
            };
            let formatType = widgets[measure];
            if (!formatType) {
                const fieldType = field.type;
                formatType = ["many2one", "reference"].includes(fieldType)
                    ? "integer"
                    : fieldType;
            }
            const codec = getFieldCodec(formatType);
            this.measureFormatters.set(measure, {
                codec,
                formatType,
                baseOptions: { field, ...codec.extractOptions(fieldInfo) },
            });
        }
    }
    /**
     * @param {{ indent: number }} cell
     * @returns {number}
     */
    getPadding(cell) {
        return 5 + cell.indent * (this.env.isSmall ? 5 : 30);
    }
    /**
     * @private
     * @param {Object} cell
     * @returns {string}
     */
    getFormattedValue(cell) {
        const { codec, formatType, baseOptions } = this.measureFormatters.get(
            cell.measure,
        );
        /** @type {Record<string, any>} */
        const formatOptions = { ...baseOptions };
        if (formatType === "monetary" && cell.currencyIds) {
            if (cell.currencyIds.length > 1) {
                formatOptions.currencyId = user.activeCompany?.currency_id;
                return /** @type {any} */ ({
                    rawValue: cell.value,
                    value: codec.format(cell.value, formatOptions),
                    currencies: cell.currencyIds,
                    help: this.getFullPrecisionHelp(cell, codec, formatOptions),
                });
            }
            formatOptions.currencyId = cell.currencyIds[0];
        }
        return /** @type {any} */ ({
            value: codec.format(cell.value, formatOptions),
            help: this.getFullPrecisionHelp(cell, codec, formatOptions),
        });
    }
    /**
     * @private
     * @param {Object} cell
     * @param {any} codec
     * @param {Record<string, any>} formatOptions
     * @returns {string|undefined}
     */
    getFullPrecisionHelp(cell, codec, formatOptions) {
        if (!formatOptions.humanReadable) {
            return undefined;
        }
        return codec.format(cell.value, { ...formatOptions, humanReadable: false });
    }

    /** @returns {Object[]} */
    get groupByItems() {
        let items = this.env.searchModel.getSearchItems(
            (searchItem) =>
                ["groupBy", "dateGroupBy"].includes(searchItem.type) &&
                !searchItem.custom &&
                !searchItem.isProperty,
        );
        if (!items.length) {
            items = [...this.fields];
        }

        let groupNumber = 1 + Math.max(0, ...items.map(({ groupNumber: n }) => n || 0));
        for (const [
            fieldName,
            customGroupBy,
        ] of this.model.metaData.customGroupBys.entries()) {
            items.push({
                ...customGroupBy,
                name: fieldName,
                groupNumber: groupNumber++,
            });
        }

        return items.map((item) => ({
            ...item,
            id: item.id || item.name,
            fieldName: item.fieldName || item.name,
            description: item.description || item.string,
            options:
                item.options ||
                (["date", "datetime"].includes(item.type)
                    ? getIntervalOptions()
                    : undefined),
        }));
    }

    /** @returns {any} the table of the model's current data */
    get table() {
        const memo = this.tableMemo;
        if (memo.epoch !== this.model.updateEpoch || !memo.table) {
            memo.epoch = this.model.updateEpoch;
            memo.table = this.model.getTable();
            this.computeMeasureFormatters();
        }
        return memo.table;
    }

    /** @returns {boolean} */
    get hideCustomGroupBy() {
        return this.env.searchModel.hideCustomGroupBy || false;
    }

    /**
     * @param {string} fieldName
     * @param {Object} field
     * @returns {boolean}
     */
    isGroupableField(fieldName, field) {
        return isGroupableField(fieldName, field);
    }

    /** @param {string} fieldName */
    onAddCustomGroupBy(fieldName) {
        this.model.addGroupBy({
            ...this.dropdown.cellInfo,
            fieldName,
            custom: true,
        });
        this.dropdown.state.close();
    }

    /**
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onGroupBySelected({ itemId, optionId }) {
        const { fieldName } = this.groupByItems.find(({ id }) => id === itemId);
        this.addGroupBy(fieldName, optionId);
    }

    /**
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onPropertyGroupBySelected({ itemId, optionId }) {
        const { fieldName } = this.env.searchModel.searchItems[itemId];
        log.logic("onPropertyGroupBySelected", () => ({ itemId, optionId, fieldName }));
        this.addGroupBy(fieldName, optionId);
    }

    /**
     * @param {string} fieldName
     * @param {string} [interval]
     */
    addGroupBy(fieldName, interval) {
        this.model.addGroupBy({ ...this.dropdown.cellInfo, fieldName, interval });
    }
    /**
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
                    target: /** @type {HTMLElement} */ (ev.target).closest(
                        ".o_pivot_header_cell_closed",
                    ),
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
    /** @param {Object} cell */
    onMeasureClick(cell) {
        this.model.sortRows({
            groupId: cell.groupId,
            measure: cell.measure,
            order: (cell.order || "desc") === "asc" ? "desc" : "asc",
        });
    }
    /** @param {MouseEvent} ev */
    onMouseEnter(ev) {
        const current = /** @type {HTMLElement} */ (ev.currentTarget);
        let index = [...current.parentNode.children].indexOf(current);
        if (current.tagName === "TH") {
            index += 1;
        }
        let cells = this.columnCellsCache.get(index);
        if (!cells) {
            cells = this.tableRef.el.querySelectorAll(`td:nth-child(${index + 1})`);
            this.columnCellsCache.set(index, cells);
        }
        cells.forEach((elt) => elt.classList.add("o_cell_hover"));
        this.hoveredCells = cells;
    }
    onMouseLeave() {
        const cells =
            this.hoveredCells ?? this.tableRef.el.querySelectorAll(".o_cell_hover");
        cells.forEach((elt) => elt.classList.remove("o_cell_hover"));
        this.hoveredCells = null;
    }

    onDownloadButtonClicked() {
        if (this.model.getTableWidth() > 16384) {
            this.notification.add(
                _t(
                    "For Excel compatibility, data cannot be exported if there are more than 16384 columns.\n\nTip: try to flip axis, filter further or reduce the number of measures.",
                ),
                { type: "danger", sticky: true },
            );
            return;
        }
        const table = this.model.exportData();
        download({
            url: "/web/pivot/export_xlsx",
            data: {
                data: new Blob([JSON.stringify(table)], {
                    type: "application/json",
                }),
            },
        });
    }
    onExpandButtonClicked() {
        this.model.expandAll();
    }
    onFlipButtonClicked() {
        this.model.flip();
    }
    /**
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
     * @param {Array} domain
     * @param {Array} views
     * @param {Object} context
     */
    openView(domain, views, context, newWindow) {
        openDrillDownView(this, domain, views, context, newWindow);
    }
    /**
     * @param {Object} cell
     * @param {boolean} [newWindow]
     */
    onOpenView(cell, newWindow) {
        if (cell.value === undefined || this.model.metaData.disableLinking) {
            return;
        }

        const context = drillDownContext(this.model.searchParams.context);
        const views = drillDownViews(this.env.config.views);

        const group = {
            rowValues: cell.groupId[0],
            colValues: cell.groupId[1],
        };
        this.openView(this.model.getGroupDomain(group), views, context, newWindow);
    }
}
