/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { CheckBoxDropdownItem } from "@web/core/dropdown/checkbox_dropdown_item";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { Field } from "@web/fields/field";
import { ViewButton } from "@web/views/view_button/view_button";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useBounceButton } from "../helpers/view_hook";

const {
    Component,
    markup,
    onPatched,
    onWillPatch,
    onWillUpdateProps,
    useExternalListener,
    useRef,
    useState,
} = owl;

const formatterRegistry = registry.category("formatters");

const DEFAULT_GROUP_PAGER_COLSPAN = 1;

const FIELD_CLASSES = {
    char: "o_list_char",
    float: "o_list_number",
    integer: "o_list_number",
    monetary: "o_list_number",
    text: "o_list_text",
    many2one: "o_list_many2one",
};

export class ListRenderer extends Component {
    setup() {
        this.allColumns = this.props.archInfo.columns;
        this.keyOptionalFields = this.createKeyOptionalFields();
        this.getOptionalActiveFields();
        this.cellClassByColumn = {};
        this.groupByButtons = this.props.archInfo.groupBy.buttons;
        this.state = useState({
            columns: this.allColumns.filter(
                (col) => !col.optional || this.optionalActiveFields[col.name]
            ),
        });
        this.withHandleColumn = this.state.columns.some((col) => col.widget === "handle");
        useExternalListener(document, "click", this.onGlobalClick.bind(this)); // capture ?
        this.tableRef = useRef("table");

        this.creates = this.props.archInfo.creates.length
            ? this.props.archInfo.creates
            : [{ description: this.env._t("Add a line") }];

        this.cellToFocus = null;
        this.activeRowId = null;
        onWillPatch(() => {
            const activeRow = document.activeElement.closest(".o_data_row.o_selected_row");
            this.activeRowId = activeRow ? activeRow.dataset.id : null;
        });
        onWillUpdateProps((nextProps) => {
            this.allColumns = nextProps.archInfo.columns;
            this.state.columns = this.allColumns.filter(
                (col) => !col.optional || this.optionalActiveFields[col.name]
            );
        });
        onPatched(() => {
            const editedRecord = this.props.list.editedRecord;
            if (editedRecord && this.activeRowId !== editedRecord.id) {
                let column = this.state.columns[0];
                if (this.cellToFocus && this.cellToFocus.record === editedRecord) {
                    column = this.cellToFocus.column;
                }
                this.focusCell(column);
            }
            this.cellToFocus = null;
        });
        const rootRef = useRef("root");
        useBounceButton(rootRef, () => {
            return this.showNoContentHelper;
        });
        this.noContentHelp = this.props.noContentHelp
            ? markup(this.props.noContentHelp)
            : undefined;
    }

    get fields() {
        return this.props.list.fields;
    }

    focusCell(column) {
        let index = this.state.columns.indexOf(column);
        if (index === -1) {
            index = 0;
        }
        const columns = [
            ...this.state.columns.slice(index, this.state.columns.length),
            ...this.state.columns.slice(0, index),
        ];
        const editedRecord = this.props.list.editedRecord;
        for (const column of columns) {
            if (column.type !== "field") {
                continue;
            }
            const fieldName = column.name;
            if (!editedRecord.isReadonly(fieldName)) {
                const fieldEl = this.tableRef.el.querySelector(
                    `.o_selected_row .o_field_widget[name=${fieldName}]`
                );
                if (fieldEl) {
                    const focusableEl = fieldEl.querySelector("input, textarea"); // .o_focusable?
                    if (focusableEl) {
                        focusableEl.focus();
                        focusableEl.select();
                        break;
                    }
                }
            }
        }
    }

    getColumnKey(column, columnIndex) {
        return column.type === "field" ? column.name : `button_group_${columnIndex}`;
    }

    editGroupRecord(group) {
        const { resId, resModel } = group.record;
        this.env.services.action.doAction({
            res_model: resModel,
            res_id: resId,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            flags: { action_buttons: true, headless: true },
        });
    }

    createKeyOptionalFields() {
        const keyParts = {
            fields: this.props.list.fieldNames,
            model: this.props.list.resModel,
            viewMode: "list",
            viewId: this.env.config.viewId,
        };

        const parts = [
            "model",
            "viewMode",
            "viewId",
            "relationalField",
            "subViewType",
            "subViewId",
        ];
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
                string: col.string,
                name: col.name,
                value: this.optionalActiveFields[col.name],
            }));
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
        let nbDisplayedRecords = list.records.length;
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
            const fieldValues = [];
            for (const value of values) {
                const fieldValue = value[fieldName];
                if (fieldValue) {
                    fieldValues.push(fieldValue);
                }
            }
            if (!fieldValues.length) {
                continue;
            }
            const type = field.type;
            if (type !== "integer" && type !== "float" && type !== "monetary") {
                continue;
            }
            const { attrs, widget } = this.props.list.activeFields[fieldName];
            const func =
                (attrs.sum && "sum") ||
                (attrs.avg && "avg") ||
                (attrs.max && "max") ||
                (attrs.min && "min");
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

                const formatter =
                    formatterRegistry.get(widget, false) || formatterRegistry.get(type, false);
                aggregates[fieldName] = {
                    help: attrs[func],
                    value: formatter ? formatter(aggregateValue) : aggregateValue,
                };
            }
        }
        return aggregates;
    }

    getGroupLevel(group) {
        return this.props.list.groupBy.length - group.list.groupBy.length - 1;
    }

    getColumnClass(column) {
        const field = this.fields[column.name];
        const classNames = [];
        if (field.sortable && column.hasLabel) {
            classNames.push("o_column_sortable");
        }
        const orderBy = this.props.list.orderBy;
        if (orderBy.length && orderBy[0].name === column.name) {
            classNames.push(orderBy[0].asc ? "o-sort-up" : "o-sort-down");
        }
        if (["float", "integer", "monetary"].includes(field.type)) {
            classNames.push("o_list_number_th");
        }
        if (column.type === "button_group") {
            classNames.push("o_list_button");
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
        // "o_selected_row" classname for the potential row in edition
        if (record.isInEdition) {
            classNames.push("o_selected_row");
        }
        if (this.props.list.model.useSampleModel) {
            classNames.push("o_sample_data_disabled");
        }
        return classNames.join(" ");
    }

    getCellClass(column) {
        if (!this.cellClassByColumn[column.id]) {
            const classNames = ["o_data_cell"];
            if (column.type === "button_group") {
                classNames.push("o_list_button");
            } else if (column.type === "field") {
                classNames.push("o_field_cell");
                if (column.attrs && column.attrs.class) {
                    classNames.push(column.attrs.class);
                }
                const typeClass = FIELD_CLASSES[this.fields[column.name].type];
                if (typeClass) {
                    classNames.push(typeClass);
                }
                if (column.widget) {
                    classNames.push("o_" + column.widget + "_cell");
                }
            }
            this.cellClassByColumn[column.id] = classNames;
        }
        return this.cellClassByColumn[column.id].join(" ");
    }

    getCellTitle(column, record) {
        const fieldName = column.name;
        const fieldType = this.fields[fieldName].type;
        if (fieldType === "boolean") {
            return "";
        }
        const formatter = formatterRegistry.get(fieldType, (val) => val);
        const formatOptions = {
            escape: false,
            data: record.data,
            isPassword: "password" in column.attrs,
            digits: column.attrs.digits && JSON.parse(column.attrs.digits),
            field: record.fields[fieldName],
        };
        return formatter(record.data[fieldName], formatOptions);
    }

    evalModifier(modifier, record) {
        return !!(modifier && new Domain(modifier).contains(record.evalContext));
    }

    get getEmptyRowIds() {
        const nbEmptyRow = Math.max(0, 4 - this.props.list.records.length);
        return Array.from(Array(nbEmptyRow).keys());
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
            colspan = Math.max(1, this.allColumns.length - DEFAULT_GROUP_PAGER_COLSPAN);
        }
        return this.props.hasSelectors ? colspan + 1 : colspan;
    }
    getGroupPagerCellColspan(group) {
        const lastAggregateIndex = this.getLastAggregateIndex(group);
        if (lastAggregateIndex > -1) {
            return this.allColumns.length - lastAggregateIndex - 1;
        } else {
            return this.allColumns.length > 1 ? DEFAULT_GROUP_PAGER_COLSPAN : 0;
        }
    }

    getOptionalActiveFields() {
        this.optionalActiveFields = {};
        let optionalActiveFields = browser.localStorage[this.keyOptionalFields];
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
    }

    onClickSortColumn(column) {
        if (this.props.list.editedRecord || this.props.list.model.useSampleModel) {
            return;
        }
        const fieldName = column.name;
        const list = this.props.list;
        if (this.fields[fieldName].sortable && column.hasLabel) {
            if (list.isGrouped) {
                const isSortable =
                    list.groups[0].getAggregates(fieldName) || list.groupBy.includes(fieldName);
                if (isSortable) {
                    list.sortBy(fieldName);
                }
            } else {
                list.sortBy(fieldName);
            }
        }
    }

    onButtonCellClicked(record, column, ev) {
        if (!ev.target.closest("button")) {
            this.onCellClicked(record, column);
        }
    }

    async onCellClicked(record, column) {
        if (this.props.editable) {
            if (record.isInEdition) {
                this.focusCell(column);
                this.cellToFocus = null;
            } else {
                await record.switchMode("edit");
                this.cellToFocus = { column, record };
            }
        } else {
            this.props.openRecord(record);
        }
    }

    saveOptionalActiveFields() {
        browser.localStorage[this.keyOptionalFields] = Object.keys(
            this.optionalActiveFields
        ).filter((fieldName) => this.optionalActiveFields[fieldName]);
    }

    get showNoContentHelper() {
        const { model } = this.props.list;
        return this.noContentHelp && (model.useSampleModel || !model.hasData());
    }

    get showTable() {
        const { model } = this.props.list;
        return model.hasData() || !this.noContentHelp;
    }

    toggleGroup(group) {
        group.toggle();
    }

    toggleSelection() {
        const list = this.props.list;
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
        record.toggleSelection();
        this.props.list.selectDomain(false);
    }

    toggleOptionalField(fieldName) {
        this.optionalActiveFields[fieldName] = !this.optionalActiveFields[fieldName];
        this.state.columns = this.allColumns.filter(
            (col) => !col.optional || this.optionalActiveFields[col.name]
        );
        this.saveOptionalActiveFields(
            this.allColumns.filter((col) => this.optionalActiveFields[col.name] && col.optional)
        );
    }

    async unselectRow() {
        if (this.props.list.editedRecord) {
            return this.props.list.editedRecord.switchMode("readonly");
        }
    }

    onGlobalClick(ev) {
        if (!this.props.list.editedRecord) {
            return; // there's no row in edition
        }
        if (this.tableRef.el.contains(ev.target)) {
            return; // ignore clicks inside the table, they are handled directly by the renderer
        }
        this.unselectRow();
    }
}

ListRenderer.template = "web.ListRenderer";
ListRenderer.components = { CheckBoxDropdownItem, Field, ViewButton, CheckBox, Dropdown };
ListRenderer.props = [
    "activeActions?",
    "list",
    "archInfo",
    "openRecord",
    "onAdd?",
    "creates?",
    "hasSelectors?",
    "editable?",
    "noContentHelp?",
];
ListRenderer.defaultProps = { hasSelectors: false };
