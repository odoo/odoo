/** @odoo-module */

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks"

import { Component, useState } from "@odoo/owl";

export class AccountReportHeader extends Component {
    static template = "account_reports.AccountReportHeader";
    static props = {};
    static components = {
        Dropdown,
        DropdownItem,
    }

    setup() {
        this.orm = useService("orm");
        this.controller = useState(this.env.controller);
    }
    // -----------------------------------------------------------------------------------------------------------------
    // Headers
    // -----------------------------------------------------------------------------------------------------------------
    get columnHeaders() {
        let columnHeaders = [];

        this.controller.options.column_headers.forEach((columnHeader, columnHeaderIndex) => {
            let columnHeadersRow = [];

            for (let i = 0; i < this.controller.columnHeadersRenderData.level_repetitions[columnHeaderIndex]; i++) {
                columnHeadersRow = [ ...columnHeadersRow, ...columnHeader];
            }

            columnHeaders.push(columnHeadersRow);
        });

        return columnHeaders;
    }

    columnHeadersColspan(column_index, header, compactOffset = 0) {
        let colspan = header.colspan || this.controller.columnHeadersRenderData.level_colspan[column_index]
        // In case of we need the total column for horizontal we need to increase the colspan of the first row
        if(this.controller.options.show_horizontal_group_total && column_index === 0) {
           colspan += 1;
        }
        return colspan;
    }

    //------------------------------------------------------------------------------------------------------------------
    // Subheaders
    //------------------------------------------------------------------------------------------------------------------
    get subheaders() {
        const columns = JSON.parse(JSON.stringify(this.controller.options.columns));
        const columnsPerGroupKey = {};

        columns.forEach((column) => {
            columnsPerGroupKey[`${column.column_group_key}_${column.expression_label}`] = column;
        });

        return this.controller.lines[0].columns.map((column) => {
            if (columnsPerGroupKey[`${column.column_group_key}_${column.expression_label}`]) {
                return columnsPerGroupKey[`${column.column_group_key}_${column.expression_label}`];
            } else {
                return {
                    expression_label: "",
                    sortable: false,
                    name: "",
                    colspan: 1,
                };
            }
        });
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Custom subheaders
    // -----------------------------------------------------------------------------------------------------------------
    get customSubheaders() {
        let customSubheaders = [];

        this.controller.columnHeadersRenderData.custom_subheaders.forEach(customSubheader => {
            customSubheaders.push(customSubheader);
        });

        return customSubheaders;
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Sortable
    // -----------------------------------------------------------------------------------------------------------------
    sortableClasses(columIndex) {
        switch (this.controller.linesCurrentOrderByColumn(columIndex)) {
            case "ASC":
                return "fa fa-long-arrow-up";
            case "DESC":
                return "fa fa-long-arrow-down";
            default:
                return "fa fa-arrows-v";
        }
    }

    async sortLinesByColumn(columnIndex, column) {
        if (column.sortable) {
            switch (this.controller.linesCurrentOrderByColumn(columnIndex)) {
                case "default":
                    await this.controller.sortLinesByColumnAsc(columnIndex);
                    break;
                case "ASC":
                    await this.controller.sortLinesByColumnDesc(columnIndex);
                    break;
                case "DESC":
                    this.controller.sortLinesByDefault();
                    break;
                default:
                    throw new Error(`Invalid value: ${ this.controller.linesCurrentOrderByColumn(columnIndex) }`);
            }
        }
    }
}
