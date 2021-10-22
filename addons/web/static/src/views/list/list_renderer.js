/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { Field } from "@web/fields/field";

const { Component } = owl;

const FIELD_CLASSES = {
    char: "o_list_char",
    float: "o_list_number",
    integer: "o_list_number",
    monetary: "o_list_number",
    text: "o_list_text",
    many2one: "o_list_many2one",
};

const DEFAULT_GROUP_PAGER_COLSPAN = 1;

export class ListRenderer extends Component {
    setup() {
        this.fields = this.props.fields;
        this.columns = this.props.info.columns;
        this.activeActions = this.props.info.activeActions;
        this.cellClassByColumn = {};
    }

    getGroupLevel(group) {
        return this.env.model.root.groupBy.length - group.groupBy.length - 1;
    }

    getColumnClass(column) {
        const classNames = [];
        if (column.sortable) {
            classNames.push("o_column_sortable");
        }
        const orderByColumn = this.props.list.orderByColumn;
        if (column.name === orderByColumn.name) {
            classNames.push(orderByColumn.asc ? "o-sort-up" : "o-sort-down");
        }
        if (["float", "integer", "monetary"].includes(this.fields[column.name].type)) {
            classNames.push("o_list_number_th");
        }
        return classNames.join(" ");
    }

    getCellClass(column) {
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
            this.cellClassByColumn[column.name] = classNames.join(" ");
        }
        return this.cellClassByColumn[column.name];
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
        return this.columns.findIndex((col) => col.name in group.aggregates);
    }
    getLastAggregateIndex(group) {
        const reversedColumns = [...this.columns].reverse(); // reverse is destructive
        const index = reversedColumns.findIndex((col) => col.name in group.aggregates);
        return index > -1 ? this.columns.length - index - 1 : -1;
    }
    getAggregateColumns(group) {
        const firstIndex = this.getFirstAggregateIndex(group);
        const lastIndex = this.getLastAggregateIndex(group);
        return this.columns.slice(firstIndex, lastIndex + 1);
    }
    getGroupNameCellColSpan(group) {
        // if there are aggregates, the first th spans until the first
        // aggregate column then all cells between aggregates are rendered
        const firstAggregateIndex = this.getFirstAggregateIndex(group);
        let colspan;
        if (firstAggregateIndex > -1) {
            colspan = firstAggregateIndex;
        } else {
            colspan = Math.max(1, this.columns.length - DEFAULT_GROUP_PAGER_COLSPAN);
        }
        return this.props.hasSelectors ? colspan + 1 : colspan;
    }
    getGroupPagerCellColspan(group) {
        const lastAggregateIndex = this.getLastAggregateIndex(group);
        if (lastAggregateIndex > -1) {
            return this.columns.length - lastAggregateIndex - 1;
        } else {
            return this.columns.length > 1 ? DEFAULT_GROUP_PAGER_COLSPAN : 0;
        }
    }

    onClickSortColumn(column) {
        this.env.model.sortByColumn(column);
    }

    openRecord(record) {
        this.props.openRecord(record);
    }

    toggleGroup(group) {
        group.toggle();
    }
}

ListRenderer.template = "web.ListRenderer";
ListRenderer.components = { CheckBox, Field };
