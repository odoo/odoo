/** @odoo-module */

import { useService } from "@web/core/utils/hooks"

import { Component, useState } from "@odoo/owl";

export class AccountReportHeader extends Component {
    static template = "account_reports.AccountReportHeader";
    static props = {};

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
        return header.colspan || this.controller.columnHeadersRenderData.level_colspan[column_index];
    }

    //------------------------------------------------------------------------------------------------------------------
    // Subheaders
    //------------------------------------------------------------------------------------------------------------------
    get subheaders() {
        let subheaders = JSON.parse(JSON.stringify(this.controller.options.columns));

        subheaders.forEach((subheader) => {
            if (subheader.figure_type === 'monetary') {
                const roundingUnit = this.controller.options.rounding_unit;

                subheader.name += ` ( ${ this.controller.options.rounding_unit_names[roundingUnit] } )`;
            }
        });

        return subheaders;
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
