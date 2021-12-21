/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { CheckBoxDropdownItem } from "@web/core/dropdown/checkbox_dropdown_item";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { Field } from "@web/fields/field";
import { ViewButton } from "@web/views/view_button/view_button";

const { Component, useState } = owl;

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
        this.fields = this.props.fields;
        this.allColumns = this.props.info.columns;
        this.keyOptionalFields = this.createKeyOptionalFields();
        this.getOptionalActiveFields();
        this.activeActions = this.props.info.activeActions;
        this.cellClassByColumn = {};
        this.groupByButtons = this.props.info.groupBy.buttons;
        this.state = useState({
            columns: this.allColumns.filter(
                (col) => !col.optional || this.optionalActiveFields[col.name]
            ),
        });
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
            const field = this.props.list.fields[fieldName];
            const type = field.type;
            if (type !== "integer" && type !== "float" && type !== "monetary") {
                continue;
            }
            const attrs = this.props.list.activeFields[fieldName].attrs;
            const func =
                (attrs.sum && "sum") ||
                (attrs.avg && "avg") ||
                (attrs.max && "max") ||
                (attrs.min && "min");
            if (func) {
                let count = 0;
                let aggregateValue = 0;
                if (func === "max") {
                    aggregateValue = -Infinity;
                } else if (func === "min") {
                    aggregateValue = Infinity;
                }
                for (const vals of values) {
                    count += 1;
                    const value = vals[fieldName];
                    if (func === "avg" || func === "sum") {
                        aggregateValue += value;
                    } else if (func === "max") {
                        aggregateValue = Math.max(aggregateValue, value);
                    } else if (func === "min") {
                        aggregateValue = Math.min(aggregateValue, value);
                    }
                }
                if (func === "avg") {
                    aggregateValue = count > 0 ? aggregateValue / count : aggregateValue;
                }
                const formatter = formatterRegistry.get(type, false);
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
        if (orderBy.length && orderBy[0].fieldName === column.name) {
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

    getRowDecoration(record) {
        return this.props.info.decorations
            .filter((decoration) => evaluateExpr(decoration.condition, record.evalContext))
            .map((decoration) => decoration.class)
            .join(" ");
    }

    getCellClass(column, record) {
        if (!this.cellClassByColumn[column.name]) {
            const classNames = ["o_data_cell"];
            if (column.type === "button_group") {
                classNames.push("o_list_button");
            } else if (column.type === "field") {
                classNames.push("o_field_cell");
                const typeClass = FIELD_CLASSES[this.fields[column.name].type];
                if (typeClass) {
                    classNames.push(typeClass);
                }
                if (column.widget) {
                    classNames.push("o_" + column.widget + "_cell");
                }
            }
            this.cellClassByColumn[column.name] = classNames;
        }
        const modifiersClassNames = [];
        if (column.type === "field") {
            const invisible = record.activeFields[column.name].modifiers.invisible;
            if (invisible && new Domain(invisible).contains(record.data)) {
                modifiersClassNames.push("o_invisible_modifier");
            }
        }

        return [...this.cellClassByColumn[column.name], ...modifiersClassNames].join(" ");
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
        return !!(modifier && new Domain(modifier).contains(record.data));
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
        const fieldName = column.name;
        const list = this.props.list;
        if (this.fields[fieldName].sortable && column.hasLabel) {
            if (list.isGrouped) {
                const isSortable =
                    list.groups[0].aggregates[fieldName] || list.groupBy.includes(fieldName);
                if (isSortable) {
                    list.sortBy(fieldName);
                }
            } else {
                list.sortBy(fieldName);
            }
        }
    }

    openRecord(record, ev) {
        if (!ev.target.closest("button")) {
            this.props.openRecord(record);
        }
    }

    saveOptionalActiveFields() {
        browser.localStorage[this.keyOptionalFields] = Object.keys(
            this.optionalActiveFields
        ).filter((fieldName) => this.optionalActiveFields[fieldName]);
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
}

ListRenderer.template = "web.ListRenderer";
ListRenderer.components = { CheckBoxDropdownItem, Field, ViewButton };
