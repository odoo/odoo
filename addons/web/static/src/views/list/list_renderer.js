/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Pager } from "@web/core/pager/pager";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable";
import { getTabableElements } from "@web/core/utils/ui";
import { Field } from "@web/views/fields/field";
import { getTooltipInfo } from "@web/views/fields/field_tooltip";
import { getClassNameFromDecoration } from "@web/views/utils";
import { ViewButton } from "@web/views/view_button/view_button";
import { useBounceButton } from "@web/views/view_hook";
import { Widget } from "@web/views/widgets/widget";
import { getFormattedValue } from "../utils";
import { localization } from "@web/core/l10n/localization";

import {
    Component,
    onMounted,
    onPatched,
    onWillPatch,
    onWillUpdateProps,
    useExternalListener,
    useRef,
    useState,
    useEffect,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const formatters = registry.category("formatters");

const DEFAULT_GROUP_PAGER_COLSPAN = 1;

const FIELD_CLASSES = {
    char: "o_list_char",
    float: "o_list_number",
    integer: "o_list_number",
    monetary: "o_list_number",
    text: "o_list_text",
    many2one: "o_list_many2one",
};

const FIXED_FIELD_COLUMN_WIDTHS = {
    boolean: "70px",
    date: "92px",
    datetime: "146px",
    float: "92px",
    integer: "74px",
    monetary: "104px",
    handle: "33px",
};

/**
 * @param {HTMLElement} parent
 */
function containsActiveElement(parent) {
    const { activeElement } = document;
    return parent !== activeElement && parent.contains(activeElement);
}

function getElementToFocus(cell) {
    return getTabableElements(cell)[0] || cell;
}

export class ListRenderer extends Component {
    setup() {
        this.uiService = useService("ui");
        this.notificationService = useService("notification");
        this.allColumns = this.props.archInfo.columns;
        this.keyOptionalFields = this.createKeyOptionalFields();
        this.getOptionalActiveFields();
        this.cellClassByColumn = {};
        this.groupByButtons = this.props.archInfo.groupBy.buttons;
        this.state = useState({
            columns: this.getActiveColumns(this.props.list),
        });
        this.withHandleColumn = this.state.columns.some((col) => col.widget === "handle");
        useExternalListener(document, "click", this.onGlobalClick.bind(this));
        this.tableRef = useRef("table");

        this.longTouchTimer = null;
        this.touchStartMs = 0;

        /**
         * When resizing, it's possible that the pointer is not above the resize
         * handle (by some few pixel difference). During this scenario, click event
         * will be triggered on the column title which will reorder the column.
         * Column resize that triggers a reorder is not a good UX and we prevent this
         * using the following state variables: `resizing` and `preventReorder` which
         * are set during the column's click (onClickSortColumn), mouseup
         * (onColumnTitleMouseUp) and onStartResize events.
         */
        this.resizing = false;
        this.preventReorder = false;

        this.creates = this.props.archInfo.creates.length
            ? this.props.archInfo.creates
            : [{ type: "create", string: this.env._t("Add a line") }];

        this.cellToFocus = null;
        this.activeRowId = null;
        onMounted(() => {
            this.activeElement = this.uiService.activeElement;
        });
        onWillPatch(() => {
            const activeRow = document.activeElement.closest(".o_data_row.o_selected_row");
            this.activeRowId = activeRow ? activeRow.dataset.id : null;
        });
        onWillUpdateProps((nextProps) => {
            this.allColumns = nextProps.archInfo.columns;
            this.state.columns = this.getActiveColumns(nextProps.list);
        });
        let dataRowId;
        this.rootRef = useRef("root");
        this.resequencePromise = Promise.resolve();
        useSortable({
            enable: () => this.canResequenceRows,
            // Params
            ref: this.rootRef,
            elements: ".o_row_draggable",
            handle: ".o_handle_cell",
            cursor: "grabbing",
            // Hooks
            onDragStart: (params) => {
                const { element } = params;
                dataRowId = element.dataset.id;
                return this.sortStart(params);
            },
            onDragEnd: (params) => this.sortStop(params),
            onDrop: (params) => this.sortDrop(dataRowId, params),
        });

        if (this.env.searchModel) {
            useBus(this.env.searchModel, "focus-view", () => {
                if (this.props.list.model.useSampleModel) {
                    return;
                }

                const nextTh = this.tableRef.el.querySelector("thead th");
                const toFocus = getElementToFocus(nextTh);
                this.focus(toFocus);
                this.tableRef.el.querySelector("tbody").classList.add("o_keyboard_navigation");
            });
        }

        // not very beautiful but works: refactor at some point
        let lastCellBeforeDialogOpening;
        useBus(this.props.list.model, "list-confirmation-dialog-will-open", () => {
            if (this.tableRef.el.contains(document.activeElement)) {
                lastCellBeforeDialogOpening = document.activeElement.closest("td");
            }
        });

        useBus(this.props.list.model, "list-confirmation-dialog-closed", () => {
            if (lastCellBeforeDialogOpening) {
                this.focus(lastCellBeforeDialogOpening);
            }
        });

        useBounceButton(this.rootRef, () => {
            return this.showNoContentHelper;
        });
        useEffect(
            (editedRecord) => {
                if (editedRecord) {
                    this.keepColumnWidths = true;
                }
            },
            () => [this.props.list.editedRecord]
        );
        useEffect(
            () => {
                this.freezeColumnWidths();
            },
            () => [this.state.columns, this.isEmpty]
        );
        useExternalListener(window, "resize", () => {
            this.columnWidths = null;
            this.freezeColumnWidths();
        });
        onPatched(() => {
            const editedRecord = this.props.list.editedRecord;
            if (editedRecord && this.activeRowId !== editedRecord.id) {
                if (this.cellToFocus && this.cellToFocus.record === editedRecord) {
                    const column = this.cellToFocus.column;
                    const forward = this.cellToFocus.forward;
                    this.focusCell(column, forward);
                } else if (this.lastEditedCell) {
                    this.focusCell(this.lastEditedCell.column, true);
                } else {
                    this.focusCell(this.state.columns[0]);
                }
            }
            this.cellToFocus = null;
            this.lastEditedCell = null;
        });
        this.isRTL = localization.direction === "rtl";
    }

    displaySaveNotification() {
        this.notificationService.add(this.env._t('Please click on the "save" button first'), {
            type: "danger",
        });
    }

    getActiveColumns(list) {
        return this.allColumns.filter((col) => {
            if (list.isGrouped && col.widget === "handle") {
                return false; // no handle column if the list is grouped
            }
            return !col.optional || this.optionalActiveFields[col.name];
        });
    }

    get hasSelectors() {
        return this.props.allowSelectors && !this.env.isSmall;
    }

    add(params) {
        if (this.canCreate) {
            this.props.onAdd(params);
        }
    }

    // The following code manipulates the DOM directly to avoid having to wait for a
    // render + patch which would occur on the next frame and cause flickering.
    freezeColumnWidths() {
        if (!this.keepColumnWidths) {
            this.columnWidths = null;
        }

        const table = this.tableRef.el;
        const headers = [...table.querySelectorAll("thead th:not(.o_list_actions_header)")];

        if (!this.columnWidths || !this.columnWidths.length) {
            // no column widths to restore

            table.style.tableLayout = "fixed";
            const allowedWidth = table.parentNode.getBoundingClientRect().width;
            // Set table layout auto and remove inline style to make sure that css
            // rules apply (e.g. fixed width of record selector)
            table.style.tableLayout = "auto";
            headers.forEach((th) => {
                th.style.width = null;
                th.style.maxWidth = null;
            });

            this.setDefaultColumnWidths();

            // Squeeze the table by applying a max-width on largest columns to
            // ensure that it doesn't overflow
            this.columnWidths = this.computeColumnWidthsFromContent(allowedWidth);
            table.style.tableLayout = "fixed";
        }
        headers.forEach((th, index) => {
            if (!th.style.width) {
                th.style.width = `${Math.floor(this.columnWidths[index])}px`;
            }
        });
    }

    setDefaultColumnWidths() {
        const widths = this.state.columns.map((col) => this.calculateColumnWidth(col));
        const sumOfRelativeWidths = widths
            .filter(({ type }) => type === "relative")
            .reduce((sum, { value }) => sum + value, 0);

        // 1 because nth-child selectors are 1-indexed, 2 when the first column contains
        // the checkboxes to select records.
        const columnOffset = this.hasSelectors ? 2 : 1;
        widths.forEach(({ type, value }, i) => {
            const headerEl = this.tableRef.el.querySelector(`th:nth-child(${i + columnOffset})`);
            if (type === "absolute") {
                if (this.isEmpty) {
                    headerEl.style.width = value;
                } else {
                    headerEl.style.minWidth = value;
                }
            } else if (type === "relative" && this.isEmpty) {
                headerEl.style.width = `${((value / sumOfRelativeWidths) * 100).toFixed(2)}%`;
            }
        });
    }

    computeColumnWidthsFromContent(allowedWidth) {
        const table = this.tableRef.el;

        // Toggle a className used to remove style that could interfere with the ideal width
        // computation algorithm (e.g. prevent text fields from being wrapped during the
        // computation, to prevent them from being completely crushed)
        table.classList.add("o_list_computing_widths");

        const headers = [...table.querySelectorAll("thead th")];
        const columnWidths = headers.map((th) => th.getBoundingClientRect().width);
        const getWidth = (th) => columnWidths[headers.indexOf(th)] || 0;
        const getTotalWidth = () => columnWidths.reduce((tot, width) => tot + width, 0);
        const shrinkColumns = (thsToShrink, shrinkAmount) => {
            let canKeepShrinking = true;
            for (const th of thsToShrink) {
                const index = headers.indexOf(th);
                let maxWidth = columnWidths[index] - shrinkAmount;
                // prevent the columns from shrinking under 92px (~ date field)
                if (maxWidth < 92) {
                    maxWidth = 92;
                    canKeepShrinking = false;
                }
                th.style.maxWidth = `${Math.floor(maxWidth)}px`;
                columnWidths[index] = maxWidth;
            }
            return canKeepShrinking;
        };
        // Sort columns, largest first
        const sortedThs = [...table.querySelectorAll("thead th:not(.o_list_button)")].sort(
            (a, b) => getWidth(b) - getWidth(a)
        );

        let totalWidth = getTotalWidth();
        for (let index = 1; totalWidth > allowedWidth; index++) {
            // Find the largest columns
            const largestCols = sortedThs.slice(0, index);
            const currentWidth = getWidth(largestCols[0]);
            for (; currentWidth === getWidth(sortedThs[index]); index++) {
                largestCols.push(sortedThs[index]);
            }

            // Compute the number of px to remove from the largest columns
            const nextLargest = sortedThs[index];
            const toRemove = Math.ceil((totalWidth - allowedWidth) / largestCols.length);
            const shrinkAmount = Math.min(toRemove, currentWidth - getWidth(nextLargest));

            // Shrink the largest columns
            const canKeepShrinking = shrinkColumns(largestCols, shrinkAmount);
            if (!canKeepShrinking) {
                break;
            }

            totalWidth = getTotalWidth();
        }

        // We are no longer computing widths, so restore the normal style
        table.classList.remove("o_list_computing_widths");
        return columnWidths;
    }

    get activeActions() {
        return this.props.activeActions || {};
    }

    get canResequenceRows() {
        if (!this.props.list.canResequence() || this.props.readonly) {
            return false;
        }
        const orderBy = this.props.list.orderBy;
        const handleField = this.props.archInfo.handleField;
        return !orderBy.length || (orderBy.length && orderBy[0].name === handleField);
    }

    /**
     * No records, no groups.
     */
    get isEmpty() {
        return !this.props.list.records.length;
    }

    get fields() {
        return this.props.list.fields;
    }

    get nbCols() {
        let nbCols = this.state.columns.length;
        if (this.hasSelectors) {
            nbCols++;
        }
        if (this.activeActions.onDelete || this.displayOptionalFields) {
            nbCols++;
        }
        return nbCols;
    }

    canUseFormatter(column, record) {
        return !record.isInEdition && !column.widget;
    }

    focusCell(column, forward = true) {
        const index = this.state.columns.indexOf(column);
        let columns;
        if (index === -1 && !forward) {
            columns = this.state.columns.slice(0).reverse();
        } else {
            columns = [
                ...this.state.columns.slice(index, this.state.columns.length),
                ...this.state.columns.slice(0, index),
            ];
        }
        const editedRecord = this.props.list.editedRecord;
        for (const column of columns) {
            if (column.type !== "field") {
                continue;
            }
            const fieldName = column.name;
            // in findNextFocusableOnRow test is done by using classList
            // refactor
            if (!editedRecord.isReadonly(fieldName)) {
                const cell = this.tableRef.el.querySelector(
                    `.o_selected_row td[name=${fieldName}]`
                );
                if (cell) {
                    const toFocus = getElementToFocus(cell);
                    if (cell !== toFocus) {
                        this.focus(toFocus);
                        this.lastEditedCell = { column, record: editedRecord };
                        break;
                    }
                }
            }
        }
    }

    focus(el) {
        el.focus();
        if (["INPUT", "TEXTAREA"].includes(el.tagName)) {
            if (el.selectionStart === null) {
                return;
            }
            if (el.selectionStart === el.selectionEnd) {
                el.selectionStart = 0;
                el.selectionEnd = el.value.length;
            }
        }
    }

    editGroupRecord(group) {
        const { resId, resModel } = group.record;
        this.env.services.action.doAction({
            context: {
                create: false,
            },
            res_model: resModel,
            res_id: resId,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            flags: { mode: "edit" },
        });
    }

    createKeyOptionalFields() {
        let keyParts = {
            fields: this.props.list.fieldNames,
            model: this.props.list.resModel,
            viewMode: "list",
            viewId: this.env.config.viewId,
        };

        if (this.props.nestedKeyOptionalFieldsData) {
            keyParts = Object.assign(keyParts, {
                model: this.props.nestedKeyOptionalFieldsData.model,
                viewMode: this.props.nestedKeyOptionalFieldsData.viewMode,
                relationalField: this.props.nestedKeyOptionalFieldsData.field,
                subViewType: "list",
            });
        }

        const parts = ["model", "viewMode", "viewId", "relationalField", "subViewType"];
        const viewIdentifier = ["optional_fields"];
        parts.forEach((partName) => {
            if (partName in keyParts) {
                viewIdentifier.push(keyParts[partName]);
            }
        });
        keyParts.fields
            .sort((left, right) => (left < right ? -1 : 1))
            .forEach((fieldName) => {
                return viewIdentifier.push(fieldName);
            });
        return viewIdentifier.join(",");
    }

    get getOptionalFields() {
        return this.allColumns
            .filter((col) => col.optional)
            .map((col) => ({
                label: col.label,
                name: col.name,
                value: this.optionalActiveFields[col.name],
            }));
    }

    get displayOptionalFields() {
        return this.getOptionalFields.length;
    }

    nbRecordsInGroup(group) {
        if (group.isFolded) {
            return 0;
        } else if (group.list.isGrouped) {
            let count = 0;
            for (const gr of group.list.groups) {
                count += this.nbRecordsInGroup(gr);
            }
            return count;
        } else {
            return group.list.records.length;
        }
    }
    get selectAll() {
        const list = this.props.list;
        const nbDisplayedRecords = list.records.length;
        if (list.isDomainSelected) {
            return true;
        } else {
            return nbDisplayedRecords > 0 && list.selection.length === nbDisplayedRecords;
        }
    }

    get aggregates() {
        let values;
        if (this.props.list.selection && this.props.list.selection.length) {
            values = this.props.list.selection.map((r) => r.data);
        } else if (this.props.list.isGrouped) {
            values = this.props.list.groups.map((g) => g.aggregates);
        } else {
            values = this.props.list.records.map((r) => r.data);
        }
        const aggregates = {};
        for (const fieldName in this.props.list.activeFields) {
            const field = this.fields[fieldName];
            const fieldValues = values.map((v) => v[fieldName]).filter((v) => v || v === 0);
            if (!fieldValues.length) {
                continue;
            }
            const type = field.type;
            if (type !== "integer" && type !== "float" && type !== "monetary") {
                continue;
            }
            const { rawAttrs, widget } = this.props.list.activeFields[fieldName];
            let currencyId;
            if (type === "monetary" || widget === "monetary") {
                const currencyField =
                    this.props.list.activeFields[fieldName].options.currency_field ||
                    this.fields[fieldName].currency_field ||
                    "currency_id";
                currencyId =
                    currencyField in this.props.list.activeFields &&
                    values[0][currencyField] &&
                    values[0][currencyField][0];
                if (currencyId) {
                    const sameCurrency = values.every(
                        (value) => currencyId === value[currencyField][0]
                    );
                    if (!sameCurrency) {
                        aggregates[fieldName] = {
                            help: _t("Different currencies cannot be aggregated"),
                            value: "—",
                        };
                        continue;
                    }
                }
            }
            const func =
                (rawAttrs.sum && "sum") ||
                (rawAttrs.avg && "avg") ||
                (rawAttrs.max && "max") ||
                (rawAttrs.min && "min");
            if (func) {
                let aggregateValue = 0;
                if (func === "max") {
                    aggregateValue = Math.max(-Infinity, ...fieldValues);
                } else if (func === "min") {
                    aggregateValue = Math.min(Infinity, ...fieldValues);
                } else if (func === "avg") {
                    aggregateValue =
                        fieldValues.reduce((acc, val) => acc + val) / fieldValues.length;
                } else if (func === "sum") {
                    aggregateValue = fieldValues.reduce((acc, val) => acc + val);
                }

                const formatter = formatters.get(widget, false) || formatters.get(type, false);
                const formatOptions = {
                    digits: rawAttrs.digits ? JSON.parse(rawAttrs.digits) : undefined,
                    escape: true,
                };
                if (currencyId) {
                    formatOptions.currencyId = currencyId;
                }
                aggregates[fieldName] = {
                    help: rawAttrs[func],
                    value: formatter ? formatter(aggregateValue, formatOptions) : aggregateValue,
                };
            }
        }
        return aggregates;
    }

    formatAggregateValue(group, column) {
        const { widget, rawAttrs } = column;
        const field = this.props.list.fields[column.name];
        const aggregateValue = group.aggregates[column.name];
        if (!(column.name in group.aggregates)) {
            return "";
        }
        const formatter = formatters.get(widget, false) || formatters.get(field.type, false);
        const formatOptions = {
            digits: rawAttrs.digits ? JSON.parse(rawAttrs.digits) : field.digits,
            escape: true,
        };
        return formatter ? formatter(aggregateValue, formatOptions) : aggregateValue;
    }

    getGroupLevel(group) {
        return this.props.list.groupBy.length - group.list.groupBy.length - 1;
    }

    getColumnClass(column) {
        const classNames = ["align-middle"];
        if (this.isSortable(column)) {
            classNames.push("o_column_sortable", "position-relative", "cursor-pointer");
        } else {
            classNames.push("cursor-default");
        }
        const orderBy = this.props.list.orderBy;
        if (
            orderBy.length &&
            column.widget !== "handle" &&
            orderBy[0].name === column.name &&
            column.hasLabel
        ) {
            classNames.push("table-active");
        }
        if (this.isNumericColumn(column)) {
            classNames.push("o_list_number_th");
        }
        if (column.type === "button_group") {
            classNames.push("o_list_button");
        }
        if (column.widget) {
            classNames.push(`o_${column.widget}_cell`);
        }

        return classNames.join(" ");
    }

    getColumns(record) {
        return this.state.columns;
    }

    isNumericColumn(column) {
        const { type } = this.fields[column.name];
        return ["float", "integer", "monetary"].includes(type);
    }

    shouldReverseHeader(column) {
        return this.isNumericColumn(column) && !this.isRTL;
    }

    isSortable(column) {
        const { hasLabel, name } = column;
        const { sortable } = this.fields[name];
        const { options } = this.props.list.activeFields[name];
        return (sortable || options.allow_order) && hasLabel;
    }

    getSortableIconClass(column) {
        const { orderBy } = this.props.list;
        const classNames = this.isSortable(column) ? ["fa", "fa-lg", "px-2"] : ["d-none"];
        if (orderBy.length && orderBy[0].name === column.name) {
            classNames.push(orderBy[0].asc ? "fa-angle-up" : "fa-angle-down");
        } else {
            classNames.push("fa-angle-down", "opacity-0", "opacity-75-hover");
        }

        return classNames.join(" ");
    }

    /**
     * Returns the classnames to apply to the row representing the given record.
     * @param {Record} record
     * @returns {string}
     */
    getRowClass(record) {
        // classnames coming from decorations
        const classNames = this.props.archInfo.decorations
            .filter((decoration) => evaluateExpr(decoration.condition, record.evalContext))
            .map((decoration) => decoration.class);
        if (record.selected) {
            classNames.push("table-info");
        }
        // "o_selected_row" classname for the potential row in edition
        if (record.isInEdition) {
            classNames.push("o_selected_row");
        }
        if (record.selected) {
            classNames.push("o_data_row_selected");
        }
        if (this.canResequenceRows) {
            classNames.push("o_row_draggable");
        }
        return classNames.join(" ");
    }

    getCellClass(column, record) {
        if (!this.cellClassByColumn[column.id]) {
            const classNames = ["o_data_cell"];
            if (column.type === "button_group") {
                classNames.push("o_list_button");
            } else if (column.type === "field") {
                classNames.push("o_field_cell");
                if (
                    column.rawAttrs &&
                    column.rawAttrs.class &&
                    this.canUseFormatter(column, record)
                ) {
                    classNames.push(column.rawAttrs.class);
                }
                const typeClass = FIELD_CLASSES[this.fields[column.name].type];
                if (typeClass) {
                    classNames.push(typeClass);
                }
                if (column.widget) {
                    classNames.push(`o_${column.widget}_cell`);
                }
            }
            this.cellClassByColumn[column.id] = classNames;
        }
        const classNames = [...this.cellClassByColumn[column.id]];
        if (column.type === "field") {
            if (record.isRequired(column.name)) {
                classNames.push("o_required_modifier");
            }
            if (record.isInvalid(column.name)) {
                classNames.push("o_invalid_cell");
            }
            if (record.isReadonly(column.name)) {
                classNames.push("o_readonly_modifier");
            }
            if (this.canUseFormatter(column, record)) {
                // generate field decorations classNames (only if field-specific decorations
                // have been defined in an attribute, e.g. decoration-danger="other_field = 5")
                // only handle the text-decoration.
                const { decorations } = record.activeFields[column.name];
                for (const decoName in decorations) {
                    if (evaluateExpr(decorations[decoName], record.evalContext)) {
                        classNames.push(getClassNameFromDecoration(decoName));
                    }
                }
            }
            if (
                record.isInEdition &&
                this.props.list.editedRecord &&
                this.props.list.editedRecord.isReadonly(column.name)
            ) {
                classNames.push("text-muted");
            } else {
                classNames.push("cursor-pointer");
            }
        }
        return classNames.join(" ");
    }

    getCellTitle(column, record) {
        const fieldType = this.fields[column.name].type;
        // Because we freeze the column sizes, it may happen that we have to shorten
        // field values. In order for the user to have access to the complete value
        // in those situations, we put the value as title of the cells.
        // This is only necessary for some field types, as for the others, we hardcode
        // a minimum column width that should be enough to display the entire value.
        // Also, we don't set title for json fields, because it's not human readable anyway.
        if (!(fieldType in FIXED_FIELD_COLUMN_WIDTHS) && fieldType != "json") {
            return this.getFormattedValue(column, record);
        }
    }

    getFieldClass(column) {
        return column.rawAttrs && column.rawAttrs.class;
    }

    getFormattedValue(column, record) {
        const fieldName = column.name;
        return getFormattedValue(record, fieldName, column.rawAttrs);
    }

    evalModifier(modifier, record) {
        return !!(modifier && new Domain(modifier).contains(record.evalContext));
    }

    getGroupDisplayName(group) {
        const { _t } = this.env;
        if (group.groupByField.type === "boolean") {
            return group.value === undefined ? _t("None") : group.value ? _t("Yes") : _t("No");
        } else {
            return group.value === undefined || group.value === false
                ? _t("None")
                : group.displayName;
        }
    }

    get canCreate() {
        return "link" in this.activeActions ? this.activeActions.link : this.activeActions.create;
    }

    get isX2Many() {
        return this.activeActions.type !== "view";
    }

    get getEmptyRowIds() {
        let nbEmptyRow = Math.max(0, 4 - this.props.list.records.length);
        if (nbEmptyRow > 0 && this.displayRowCreates) {
            nbEmptyRow -= 1;
        }
        return Array.from(Array(nbEmptyRow).keys());
    }

    get displayRowCreates() {
        return this.isX2Many && this.canCreate;
    }

    // Group headers logic:
    // if there are aggregates, the first th spans until the first
    // aggregate column then all cells between aggregates are rendered
    // a single cell is rendered after the last aggregated column to render the
    // pager (with adequate colspan)
    // ex:
    // TH TH TH TH TH AGG AGG TH AGG AGG TH TH TH
    // 0  1  2  3  4   5   6   7  8   9  10 11 12
    // [    TH 5    ][TH][TH][TH][TH][TH][ TH 3 ]
    // [ group name ][ aggregate cells  ][ pager]
    // TODO: move this somewhere, compute this only once (same result for each groups actually) ?
    getFirstAggregateIndex(group) {
        return this.state.columns.findIndex((col) => col.name in group.aggregates);
    }
    getLastAggregateIndex(group) {
        const reversedColumns = [...this.state.columns].reverse(); // reverse is destructive
        const index = reversedColumns.findIndex((col) => col.name in group.aggregates);
        return index > -1 ? this.state.columns.length - index - 1 : -1;
    }
    getAggregateColumns(group) {
        const firstIndex = this.getFirstAggregateIndex(group);
        const lastIndex = this.getLastAggregateIndex(group);
        return this.state.columns.slice(firstIndex, lastIndex + 1);
    }
    getGroupNameCellColSpan(group) {
        // if there are aggregates, the first th spans until the first
        // aggregate column then all cells between aggregates are rendered
        const firstAggregateIndex = this.getFirstAggregateIndex(group);
        let colspan;
        if (firstAggregateIndex > -1) {
            colspan = firstAggregateIndex;
        } else {
            colspan = Math.max(1, this.state.columns.length - DEFAULT_GROUP_PAGER_COLSPAN);
            if (this.displayOptionalFields) {
                colspan++;
            }
        }
        if (this.hasSelectors) {
            colspan++;
        }
        return colspan;
    }
    getGroupPagerCellColspan(group) {
        const lastAggregateIndex = this.getLastAggregateIndex(group);
        if (lastAggregateIndex > -1) {
            let colspan = this.state.columns.length - lastAggregateIndex - 1;
            if (this.displayOptionalFields) {
                colspan++;
            }
            return colspan;
        } else {
            return this.state.columns.length > 1 ? DEFAULT_GROUP_PAGER_COLSPAN : 0;
        }
    }

    getGroupPagerProps(group) {
        const list = group.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: group.count,
            onUpdate: async ({ offset, limit }) => {
                await list.load({ limit, offset });
                this.render(true);
            },
            withAccessKey: false,
        };
    }

    getOptionalActiveFields() {
        this.optionalActiveFields = {};
        let optionalActiveFields = browser.localStorage.getItem(this.keyOptionalFields);
        if (optionalActiveFields) {
            optionalActiveFields = optionalActiveFields.split(",");
            this.allColumns.forEach((col) => {
                this.optionalActiveFields[col.name] = optionalActiveFields.includes(col.name);
            });
        } else {
            this.allColumns.forEach((col) => {
                this.optionalActiveFields[col.name] = col.optional === "show";
            });
        }
        if (this.props.onOptionalFieldsChanged) {
            this.props.onOptionalFieldsChanged(this.optionalActiveFields);
        }
    }

    onClickSortColumn(column) {
        if (this.preventReorder) {
            this.preventReorder = false;
            return;
        }
        if (this.props.list.editedRecord || this.props.list.model.useSampleModel) {
            return;
        }
        const fieldName = column.name;
        const list = this.props.list;
        if (this.isSortable(column)) {
            list.sortBy(fieldName);
        }
    }

    onButtonCellClicked(record, column, ev) {
        if (!ev.target.closest("button")) {
            this.onCellClicked(record, column, ev);
        }
    }

    async onCellClicked(record, column, ev) {
        if (ev.target.special_click) {
            return;
        }
        const recordAfterResequence = async () => {
            const recordIndex = this.props.list.records.indexOf(record);
            await this.resequencePromise;
            // row might have changed record after resequence
            record = this.props.list.records[recordIndex] || record;
        };

        if ((this.props.list.model.multiEdit && record.selected) || this.isInlineEditable(record)) {
            if (record.isInEdition && this.props.list.editedRecord === record) {
                const cell = this.tableRef.el.querySelector(
                    `.o_selected_row td[name='${column.name}']`
                );
                if (cell && containsActiveElement(cell)) {
                    this.lastEditedCell = { column, record };
                    // Cell is already focused.
                    return;
                }
                this.focusCell(column);
                this.cellToFocus = null;
            } else {
                await recordAfterResequence();
                await record.switchMode("edit");
                this.cellToFocus = { column, record };
            }
        } else if (this.props.list.editedRecord && this.props.list.editedRecord !== record) {
            this.props.list.unselectRecord(true);
        } else if (!this.props.archInfo.noOpen) {
            this.props.openRecord(record);
        }
    }

    async onDeleteRecord(record) {
        this.keepColumnWidths = true;
        const editedRecord = this.props.list.editedRecord;
        if (editedRecord && editedRecord !== record) {
            const unselected = await this.props.list.unselectRecord(true);
            if (!unselected) {
                return;
            }
        }
        if (this.activeActions.onDelete) {
            this.activeActions.onDelete(record);
        }
    }

    /**
     * @param {HTMLTableCellElement} cell
     * @param {boolean} cellIsInGroupRow
     * @param {"up"|"down"|"left"|"right"} direction
     */
    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        const row = cell.parentElement;
        const children = [...row.children];
        const index = children.indexOf(cell);
        let futureCell;
        switch (direction) {
            case "up": {
                let futureRow = row.previousElementSibling;
                futureRow =
                    futureRow ||
                    (row.parentElement.previousElementSibling &&
                        row.parentElement.previousElementSibling.lastElementChild);

                if (futureRow) {
                    const addCell = [...futureRow.children].find((c) =>
                        c.classList.contains("o_group_field_row_add")
                    );
                    const nextIsGroup = futureRow.classList.contains("o_group_header");
                    const rowTypeSwitched = cellIsInGroupRow !== nextIsGroup;
                    let defaultIndex = 0;
                    if (cellIsInGroupRow) {
                        defaultIndex = this.hasSelectors ? 1 : 0;
                    }
                    futureCell =
                        addCell ||
                        (futureRow && futureRow.children[rowTypeSwitched ? defaultIndex : index]);
                }
                break;
            }
            case "down": {
                let futureRow = row.nextElementSibling;
                futureRow =
                    futureRow ||
                    (row.parentElement.nextElementSibling &&
                        row.parentElement.nextElementSibling.firstElementChild);
                if (futureRow) {
                    const addCell = [...futureRow.children].find((c) =>
                        c.classList.contains("o_group_field_row_add")
                    );
                    const nextIsGroup = futureRow.classList.contains("o_group_header");
                    const rowTypeSwitched = cellIsInGroupRow !== nextIsGroup;
                    let defaultIndex = 0;
                    if (cellIsInGroupRow) {
                        defaultIndex = this.hasSelectors ? 1 : 0;
                    }
                    futureCell =
                        addCell ||
                        (futureRow && futureRow.children[rowTypeSwitched ? defaultIndex : index]);
                }
                break;
            }
            case "left": {
                futureCell = children[index - 1];
                break;
            }
            case "right": {
                futureCell = children[index + 1];
                break;
            }
        }
        return futureCell && getElementToFocus(futureCell);
    }

    isInlineEditable(record) {
        // /!\ the keyboard navigation works under the hypothesis that all or
        // none records are editable.
        return !!this.props.editable;
    }

    /**
     * @param {KeyboardEvent} ev
     * @param { import('@web/views/relational_model').Group
     *  | null
     * } group
     * @param { import('@web/views/relational_model').Record
     *  | import('@web/views/basic_relational_model').Record
     *  | null
     * } record
     */
    onCellKeydown(ev, group = null, record = null) {
        if (this.props.list.model.useSampleModel) {
            return;
        }

        const hotkey = getActiveHotkey(ev);

        if (ev.target.tagName === "TEXTAREA" && hotkey === "enter") {
            return;
        }

        const closestCell = ev.target.closest("td, th");

        const handled = this.props.list.editedRecord
            ? this.onCellKeydownEditMode(hotkey, closestCell, group, record)
            : this.onCellKeydownReadOnlyMode(hotkey, closestCell, group, record); // record is supposed to be not null here

        if (handled) {
            this.lastCreatingAction = false;
            this.tableRef.el.querySelector("tbody").classList.add("o_keyboard_navigation");
            ev.preventDefault();
            ev.stopPropagation();
        }
    }

    findNextFocusableOnRow(row, cell) {
        const children = [...row.children];
        const index = children.indexOf(cell);
        const nextCells = children.slice(index + 1);
        for (const c of nextCells) {
            if (!c.classList.contains("o_data_cell")) {
                continue;
            }
            if (
                c.firstElementChild &&
                c.firstElementChild.classList.contains("o_readonly_modifier")
            ) {
                continue;
            }
            const toFocus = getElementToFocus(c);
            if (toFocus !== c) {
                return toFocus;
            }
        }
        return null;
    }

    findPreviousFocusableOnRow(row, cell) {
        const children = [...row.children];
        const index = children.indexOf(cell);
        const previousCells = children.slice(0, index);
        for (const c of previousCells.reverse()) {
            if (!c.classList.contains("o_data_cell")) {
                continue;
            }
            if (
                c.firstElementChild &&
                c.firstElementChild.classList.contains("o_readonly_modifier")
            ) {
                continue;
            }
            const toFocus = getElementToFocus(c);
            if (toFocus !== c) {
                return toFocus;
            }
        }
        return null;
    }

    applyCellKeydownMultiEditMode(hotkey, cell, group, record) {
        const { list } = this.props;
        const row = cell.parentElement;
        let toFocus, futureRecord;
        const index = list.selection.indexOf(record);
        if (this.lastIsDirty && ["tab", "shift+tab", "enter"].includes(hotkey)) {
            record.switchMode("readonly");
            return true;
        }

        if (this.applyCellKeydownEditModeStayOnRow(hotkey, cell, group, record)) {
            return true;
        }

        switch (hotkey) {
            case "tab":
                futureRecord = list.selection[index + 1] || list.selection[0];
                if (record === futureRecord) {
                    // Refocus first cell of same record
                    toFocus = this.findNextFocusableOnRow(row);
                    this.focus(toFocus);
                    return true;
                }
                break;

            case "shift+tab":
                futureRecord =
                    list.selection[index - 1] || list.selection[list.selection.length - 1];
                if (record === futureRecord) {
                    // Refocus last cell of same record
                    toFocus = this.findPreviousFocusableOnRow(row);
                    this.focus(toFocus);
                    return true;
                }
                this.cellToFocus = { forward: false, record: futureRecord };
                break;

            case "enter":
                if (list.selection.length === 1) {
                    record.switchMode("readonly");
                    return true;
                }
                futureRecord = list.selection[index + 1] || list.selection[0];
                break;
        }

        if (futureRecord) {
            futureRecord.switchMode("edit");
            return true;
        }
        return false;
    }

    applyCellKeydownEditModeGroup(hotkey, _cell, group, record) {
        const { editable } = this.props;
        const groupIndex = group.list.records.indexOf(record);
        const isLastOfGroup = groupIndex === group.list.records.length - 1;
        const isDirty = record.isDirty || this.lastIsDirty;
        const isEnterBehavior = hotkey === "enter" && (!record.canBeAbandoned || isDirty);
        const isTabBehavior = hotkey === "tab" && !record.canBeAbandoned && isDirty;
        if (isEnterBehavior && !record.checkValidity()) {
            return true;
        }
        if (
            isLastOfGroup &&
            this.canCreate &&
            editable === "bottom" &&
            record.checkValidity() &&
            (isEnterBehavior || isTabBehavior)
        ) {
            this.add({ group });
            return true;
        }
        return false;
    }

    applyCellKeydownEditModeStayOnRow(hotkey, cell, group, record) {
        let toFocus;
        const row = cell.parentElement;

        switch (hotkey) {
            case "tab":
                toFocus = this.findNextFocusableOnRow(row, cell);
                break;
            case "shift+tab":
                toFocus = this.findPreviousFocusableOnRow(row, cell);
                break;
        }

        if (toFocus) {
            this.focus(toFocus);
            return true;
        }
        return false;
    }

    /**
     * @param {string} hotkey
     * @param {HTMLTableCellElement} cell
     * @param { import('@web/views/relational_model').Group
     *  | null
     * } group
     * @param { import('@web/views/relational_model').Record
     *  | import('@web/views/basic_relational_model').Record
     * } record
     * @returns {boolean} true if some behavior has been taken
     */
    onCellKeydownEditMode(hotkey, cell, group, record) {
        const { cycleOnTab, list } = this.props;
        const row = cell.parentElement;
        const applyMultiEditBehavior = record && record.selected && list.model.multiEdit;
        const topReCreate = this.props.editable === "top" && record.isNew;

        if (
            applyMultiEditBehavior &&
            this.applyCellKeydownMultiEditMode(hotkey, cell, group, record)
        ) {
            return true;
        }

        if (this.applyCellKeydownEditModeStayOnRow(hotkey, cell, group, record)) {
            return true;
        }

        if (group && this.applyCellKeydownEditModeGroup(hotkey, cell, group, record)) {
            return true;
        }

        switch (hotkey) {
            case "tab": {
                const index = list.records.indexOf(record);
                const lastIndex = topReCreate ? 0 : list.records.length - 1;
                if (index === lastIndex) {
                    if (this.displayRowCreates) {
                        if (record.isNew && !record.isDirty) {
                            list.unselectRecord(true);
                            return false;
                        }
                        // add a line
                        if (record.checkValidity()) {
                            const { context } = this.creates[0];
                            this.add({ context });
                        }
                    } else if (
                        this.canCreate &&
                        !record.canBeAbandoned &&
                        (record.isDirty || this.lastIsDirty)
                    ) {
                        this.add({ group });
                    } else if (cycleOnTab) {
                        if (record.canBeAbandoned) {
                            list.unselectRecord(true);
                        }
                        const futureRecord = list.records[0];
                        if (record === futureRecord) {
                            // Refocus first cell of same record
                            const toFocus = this.findNextFocusableOnRow(row);
                            this.focus(toFocus);
                        } else {
                            futureRecord.switchMode("edit");
                        }
                    } else {
                        return false;
                    }
                } else {
                    const futureRecord = list.records[index + 1];
                    futureRecord.switchMode("edit");
                }
                break;
            }
            case "shift+tab": {
                const index = list.records.indexOf(record);
                if (index === 0) {
                    if (cycleOnTab) {
                        if (record.canBeAbandoned) {
                            list.unselectRecord(true);
                        }
                        const futureRecord = list.records[list.records.length - 1];
                        if (record === futureRecord) {
                            // Refocus first cell of same record
                            const toFocus = this.findPreviousFocusableOnRow(row);
                            this.focus(toFocus);
                        } else {
                            this.cellToFocus = { forward: false, record: futureRecord };
                            futureRecord.switchMode("edit");
                        }
                    } else {
                        list.unselectRecord(true);
                        return false;
                    }
                } else {
                    const futureRecord = list.records[index - 1];
                    this.cellToFocus = { forward: false, record: futureRecord };
                    futureRecord.switchMode("edit");
                }
                break;
            }
            case "enter": {
                const index = list.records.indexOf(record);
                let futureRecord = list.records[index + 1];
                if (topReCreate && index === 0) {
                    futureRecord = null;
                }

                if (!futureRecord && !this.canCreate) {
                    futureRecord = list.records[0];
                }

                if (futureRecord) {
                    futureRecord.switchMode("edit", { checkValidity: true });
                } else if (this.lastIsDirty || !record.canBeAbandoned || this.displayRowCreates) {
                    this.add({ group });
                } else {
                    futureRecord = list.records.at(0);
                    futureRecord.switchMode("edit", { checkValidity: true });
                }
                break;
            }
            case "escape": {
                // TODO this seems bad: refactor this
                record.discard();
                list.unselectRecord(true);
                const firstAddButton = this.tableRef.el.querySelector(
                    ".o_field_x2many_list_row_add a"
                );

                if (firstAddButton) {
                    this.focus(firstAddButton);
                } else if (group && record.isNew) {
                    const children = [...row.parentElement.children];
                    const index = children.indexOf(row);
                    for (let i = index + 1; i < children.length; i++) {
                        const row = children[i];
                        if (row.classList.contains("o_group_header")) {
                            break;
                        }
                        const addCell = [...row.children].find((c) =>
                            c.classList.contains("o_group_field_row_add")
                        );
                        if (addCell) {
                            const toFocus = addCell.querySelector("a");
                            this.focus(toFocus);
                            return true;
                        }
                    }
                    this.focus(cell);
                } else {
                    this.focus(cell);
                }
                break;
            }
            default:
                return false;
        }
        return true;
    }

    /**
     * @param {string} hotkey
     * @param {HTMLTableCellElement} cell
     * @param { import('@web/views/relational_model').Group
     *  | null
     * } group
     * @param { import('@web/views/relational_model').Record
     *  | import('@web/views/basic_relational_model').Record
     *  | null
     * } record
     * @returns {boolean} true if some behavior has been taken
     */
    onCellKeydownReadOnlyMode(hotkey, cell, group, record) {
        const cellIsInGroupRow = Boolean(group && !record);
        const applyMultiEditBehavior = record && record.selected && this.props.list.model.multiEdit;
        let toFocus;
        switch (hotkey) {
            case "arrowup":
                toFocus = this.findFocusFutureCell(cell, cellIsInGroupRow, "up");
                if (!toFocus && this.env.searchModel) {
                    this.env.searchModel.trigger("focus-search");
                    return true;
                }
                break;
            case "arrowdown":
                toFocus = this.findFocusFutureCell(cell, cellIsInGroupRow, "down");
                break;
            case "arrowleft":
                if (cellIsInGroupRow && !group.isFolded) {
                    this.toggleGroup(group);
                    return true;
                }

                if (cell.classList.contains("o_field_x2many_list_row_add")) {
                    // to refactor
                    const a = document.activeElement;
                    toFocus = a.previousElementSibling;
                } else {
                    toFocus = this.findFocusFutureCell(cell, cellIsInGroupRow, "left");
                }
                break;
            case "arrowright":
                if (cellIsInGroupRow && group.isFolded) {
                    this.toggleGroup(group);
                    return true;
                }

                if (cell.classList.contains("o_field_x2many_list_row_add")) {
                    // This cell contains only <a/> elements, see template.
                    const a = document.activeElement;
                    toFocus = a.nextElementSibling;
                } else {
                    toFocus = this.findFocusFutureCell(cell, cellIsInGroupRow, "right");
                }
                break;
            case "tab":
                if (cellIsInGroupRow) {
                    const buttons = Array.from(cell.querySelectorAll(".o_group_buttons button"));
                    const currentButton = document.activeElement.closest("button");
                    const index = buttons.indexOf(currentButton);
                    toFocus = buttons[index + 1] || currentButton;
                }
                break;
            case "shift+tab":
                if (cellIsInGroupRow) {
                    const buttons = Array.from(cell.querySelectorAll(".o_group_buttons button"));
                    const currentButton = document.activeElement.closest("button");
                    const index = buttons.indexOf(currentButton);
                    toFocus = buttons[index - 1] || currentButton;
                }
                break;
            case "enter":
                if (!group && !record) {
                    return false;
                }

                if (cell.classList.contains("o_list_record_remove")) {
                    this.onDeleteRecord(record);
                    return true;
                }

                if (cellIsInGroupRow) {
                    const button = document.activeElement.closest("button");
                    if (button) {
                        button.click();
                    } else {
                        this.toggleGroup(group);
                    }
                    return true;
                }

                if (this.isInlineEditable(record) || applyMultiEditBehavior) {
                    const column = this.state.columns.find(
                        (c) => c.name === cell.getAttribute("name")
                    );
                    this.cellToFocus = { column, record };
                    record.switchMode("edit");
                    return true;
                }

                if (!this.props.archInfo.noOpen) {
                    this.props.openRecord(record);
                    return true;
                }
                break;
            default:
                // Return with no effect (no stop or prevent default...)
                return false;
        }

        if (toFocus) {
            this.focus(toFocus);
            return true;
        }

        return false;
    }

    async onCreateAction(context) {
        // TO DISCUSS: is it a use case for owl `batched()` ?
        if (this.createProm) {
            return;
        }
        this.add({ context });
        this.createProm = Promise.resolve();
        this.createProm.then(() => {
            this.lastCreatingAction = true;
        });
        await this.createProm;
        this.createProm = null;
    }

    /**
     * @param {FocusEvent & {
     *  target: HTMLElement,
     *  relatedTarget: HTMLElement | null
     * }} ev
     */
    onFocusIn(ev) {
        const { relatedTarget, target } = ev;
        const fromOutside = !this.rootRef.el.contains(relatedTarget);
        if (!fromOutside) {
            return;
        }

        const isX2MRowAdder =
            target.tagName === "A" &&
            target.parentElement.classList.contains("o_field_x2many_list_row_add");
        const withinSameUIActiveElement =
            this.uiService.getActiveElementOf(relatedTarget) === this.activeElement;
        if (withinSameUIActiveElement && isX2MRowAdder) {
            const { context } = this.creates[0];
            this.onCreateAction(context);
        }
    }

    setDirty(isDirty) {
        this.lastIsDirty = isDirty;
    }

    saveOptionalActiveFields() {
        browser.localStorage.setItem(
            this.keyOptionalFields,
            Object.keys(this.optionalActiveFields).filter(
                (fieldName) => this.optionalActiveFields[fieldName]
            )
        );
    }

    get showNoContentHelper() {
        const { model } = this.props.list;
        return this.props.noContentHelp && (model.useSampleModel || !model.hasData());
    }

    showGroupPager(group) {
        return !group.isFolded && group.list.limit < group.count;
    }

    toggleGroup(group) {
        group.toggle();
    }

    get canSelectRecord() {
        return !this.props.list.editedRecord && !this.props.list.model.useSampleModel;
    }

    toggleSelection() {
        const list = this.props.list;
        if (!this.canSelectRecord) {
            return;
        }
        if (list.selection.length === list.records.length) {
            list.records.forEach((record) => {
                record.toggleSelection(false);
                list.selectDomain(false);
            });
        } else {
            list.records.forEach((record) => {
                record.toggleSelection(true);
            });
        }
    }

    toggleRecordSelection(record) {
        if (!this.canSelectRecord) {
            return;
        }
        record.toggleSelection();
        this.props.list.selectDomain(false);
    }

    async toggleOptionalField(fieldName) {
        this.optionalActiveFields[fieldName] = !this.optionalActiveFields[fieldName];
        if (this.props.onOptionalFieldsChanged) {
            this.props.onOptionalFieldsChanged(this.optionalActiveFields);
        }
        this.state.columns = this.getActiveColumns(this.props.list);
        this.saveOptionalActiveFields(
            this.allColumns.filter((col) => this.optionalActiveFields[col.name] && col.optional)
        );
    }

    onGlobalClick(ev) {
        if (!this.props.list.editedRecord) {
            return; // there's no row in edition
        }

        this.tableRef.el.querySelector("tbody").classList.remove("o_keyboard_navigation");

        const target = ev.target;
        if (this.tableRef.el.contains(target) && target.closest(".o_data_row")) {
            // ignore clicks inside the table that are originating from a record row
            // as they are handled directly by the renderer.
            return;
        }
        if (this.activeElement !== this.uiService.activeElement) {
            return;
        }
        // Legacy DatePicker
        if (target.closest(".daterangepicker")) {
            return;
        }
        // Legacy autocomplete
        if (ev.target.closest(".ui-autocomplete")) {
            return;
        }
        this.props.list.unselectRecord(true);
    }

    calculateColumnWidth(column) {
        if (column.options && column.rawAttrs.width) {
            return { type: "absolute", value: column.rawAttrs.width };
        }

        if (column.type !== "field") {
            return { type: "relative", value: 1 };
        }

        const type = column.widget || this.props.list.fields[column.name].type;
        if (type in FIXED_FIELD_COLUMN_WIDTHS) {
            return { type: "absolute", value: FIXED_FIELD_COLUMN_WIDTHS[type] };
        }

        return { type: "relative", value: 1 };
    }

    get isDebugMode() {
        return Boolean(odoo.debug);
    }

    makeTooltip(column) {
        return getTooltipInfo({
            viewMode: "list",
            resModel: this.props.list.resModel,
            field: this.props.list.fields[column.name],
            fieldInfo: this.props.list.activeFields[column.name],
        });
    }

    /**
     * Handles the :hover effect on sortable column headers
     *
     * @private
     * @param {MouseEvent} ev
     */
    onHoverSortColumn(ev, column) {
        if (this.props.list.orderBy.length && this.props.list.orderBy[0].name === column.name) {
            return;
        } else if (this.isSortable(column) && column.widget !== "handle") {
            ev.target.classList.toggle("table-active", ev.type == "mouseenter");
        }
    }

    onColumnTitleMouseUp() {
        if (this.resizing) {
            this.preventReorder = true;
        }
    }

    /**
     * Handles the resize feature on the column headers
     *
     * @private
     * @param {MouseEvent} ev
     */
    onStartResize(ev) {
        this.resizing = true;
        const table = this.tableRef.el;
        const th = ev.target.closest("th");
        const handler = th.querySelector(".o_resize");
        table.style.width = `${Math.floor(table.getBoundingClientRect().width)}px`;
        const thPosition = [...th.parentNode.children].indexOf(th);
        const resizingColumnElements = [...table.getElementsByTagName("tr")]
            .filter((tr) => tr.children.length === th.parentNode.children.length)
            .map((tr) => tr.children[thPosition]);
        const initialX = ev.clientX;
        const initialWidth = th.getBoundingClientRect().width;
        const initialTableWidth = table.getBoundingClientRect().width;
        const resizeStoppingEvents = ["keydown", "mousedown", "mouseup"];

        // fix the width so that if the resize overflows, it doesn't affect the layout of the parent
        if (!this.rootRef.el.style.width) {
            this.rootRef.el.style.width = `${Math.floor(
                this.rootRef.el.getBoundingClientRect().width
            )}px`;
        }

        // Apply classes to table and selected column
        table.classList.add("o_resizing");
        for (const el of resizingColumnElements) {
            el.classList.add("o_column_resizing");
            handler.classList.add("bg-primary", "opacity-100");
            handler.classList.remove("bg-black-25", "opacity-50-hover");
        }
        // Mousemove event : resize header
        const resizeHeader = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const delta = ev.clientX - initialX;
            const newWidth = Math.max(10, initialWidth + delta);
            const tableDelta = newWidth - initialWidth;
            th.style.width = `${Math.floor(newWidth)}px`;
            th.style.maxWidth = `${Math.floor(newWidth)}px`;
            table.style.width = `${Math.floor(initialTableWidth + tableDelta)}px`;
        };
        window.addEventListener("mousemove", resizeHeader);

        // Mouse or keyboard events : stop resize
        const stopResize = (ev) => {
            this.resizing = false;
            // freeze column size after resizing
            this.keepColumnWidths = true;
            // Ignores the 'left mouse button down' event as it used to start resizing
            if (ev.type === "mousedown" && ev.which === 1) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            table.classList.remove("o_resizing");
            for (const el of resizingColumnElements) {
                el.classList.remove("o_column_resizing");
                handler.classList.remove("bg-primary", "opacity-100");
                handler.classList.add("bg-black-25", "opacity-50-hover");
            }

            window.removeEventListener("mousemove", resizeHeader);
            for (const eventType of resizeStoppingEvents) {
                window.removeEventListener(eventType, stopResize);
            }

            // we remove the focus to make sure that the there is no focus inside
            // the tr.  If that is the case, there is some css to darken the whole
            // thead, and it looks quite weird with the small css hover effect.
            document.activeElement.blur();
        };
        // We have to listen to several events to properly stop the resizing function. Those are:
        // - mousedown (e.g. pressing right click)
        // - mouseup : logical flow of the resizing feature (drag & drop)
        // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
        for (const eventType of resizeStoppingEvents) {
            window.addEventListener(eventType, stopResize);
        }
    }

    resetLongTouchTimer() {
        if (this.longTouchTimer) {
            browser.clearTimeout(this.longTouchTimer);
            this.longTouchTimer = null;
        }
    }

    onRowTouchStart(record, ev) {
        if (!this.props.allowSelectors) {
            return;
        }
        if (this.props.list.selection.length) {
            ev.stopPropagation(); // This is done in order to prevent the tooltip from showing up
        }
        this.touchStartMs = Date.now();
        if (this.longTouchTimer === null) {
            this.longTouchTimer = browser.setTimeout(() => {
                this.toggleRecordSelection(record);
                this.resetLongTouchTimer();
            }, this.constructor.LONG_TOUCH_THRESHOLD);
        }
    }
    onRowTouchEnd(record) {
        const elapsedTime = Date.now() - this.touchStartMs;
        if (elapsedTime < this.constructor.LONG_TOUCH_THRESHOLD) {
            this.resetLongTouchTimer();
        }
    }
    onRowTouchMove(record) {
        this.resetLongTouchTimer();
    }

    /**
     * @param {string} dataRowId
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     * @param {HTMLElement} [params.next]
     * @param {HTMLElement} [params.parent]
     * @param {HTMLElement} [params.previous]
     */
    async sortDrop(dataRowId, { element, previous }) {
        if (this.props.list.editedRecord) {
            this.props.list.unselectRecord(true);
        }
        element.classList.remove("o_row_draggable");
        const refId = previous ? previous.dataset.id : null;
        this.resequencePromise = this.props.list.resequence(dataRowId, refId, {
            handleField: this.props.archInfo.handleField,
        });
        await this.resequencePromise;
        element.classList.add("o_row_draggable");
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     */
    sortStart({ element }) {
        element.classList.add("o_dragged");
        const table = this.tableRef.el;
        const headers = [...table.querySelectorAll("thead th")];
        const cells = [...element.querySelectorAll("td")];
        let headerIndex = 0;
        for (const cell of cells) {
            let width = 0;
            for (let i = 0; i < cell.colSpan; i++) {
                const header = headers[headerIndex + i];
                const style = getComputedStyle(header);
                width += parseFloat(style.width);
            }
            cell.style.width = `${width}px`;
            headerIndex += cell.colSpan;
        }
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     */
    sortStop({ element }) {
        element.classList.remove("o_dragged");
        for (const cell of element.querySelectorAll("td")) {
            cell.style.width = null;
        }
    }

    ignoreEventInSelectionMode(ev) {
        const { list } = this.props;
        if (this.env.isSmall && list.selection && list.selection.length) {
            // in selection mode, only selection is allowed.
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    onClickCapture(record, ev) {
        const { list } = this.props;
        if (this.env.isSmall && list.selection && list.selection.length) {
            ev.stopPropagation();
            ev.preventDefault();
            this.toggleRecordSelection(record);
        }
    }
}

ListRenderer.template = "web.ListRenderer";

ListRenderer.rowsTemplate = "web.ListRenderer.Rows";
ListRenderer.recordRowTemplate = "web.ListRenderer.RecordRow";
ListRenderer.groupRowTemplate = "web.ListRenderer.GroupRow";

ListRenderer.components = { DropdownItem, Field, ViewButton, CheckBox, Dropdown, Pager, Widget };
ListRenderer.props = [
    "activeActions?",
    "list",
    "archInfo",
    "openRecord",
    "onAdd?",
    "cycleOnTab?",
    "allowSelectors?",
    "editable?",
    "noContentHelp?",
    "nestedKeyOptionalFieldsData?",
    "readonly?",
    "onOptionalFieldsChanged?",
];
ListRenderer.defaultProps = { hasSelectors: false, cycleOnTab: true };

ListRenderer.LONG_TOUCH_THRESHOLD = 400;
