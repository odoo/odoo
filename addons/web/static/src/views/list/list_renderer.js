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

export class ListRenderer extends Component {
    setup() {
        this.fields = this.props.fields;
        this.columns = this.props.info.columns;
        this.activeActions = this.props.info.activeActions;
        this.cellClassByColumn = {};
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
