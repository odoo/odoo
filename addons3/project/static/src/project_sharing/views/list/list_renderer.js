/** @odoo-module */

import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillUpdateProps } from "@odoo/owl";

export class ProjectSharingListRenderer extends ListRenderer {
    setup() {
        super.setup(...arguments);
        this.setColumns(this.allColumns);
        onWillUpdateProps((nextProps) => {
            this.setColumns(nextProps.archInfo.columns);
        });
    }

    setColumns(columns) {
        if (this.props.list.records.length) {
            const allColumns = [];
            const firstRecord = this.props.list.records[0];
            for (const column of columns) {
                if (evaluateBooleanExpr(column.column_invisible, firstRecord.evalContextWithVirtualIds)) {
                    continue;
                }
                allColumns.push(column);
            }
            this.allColumns = allColumns;
        } else {
            this.allColumns = columns;
        }
        this.state.columns = this.allColumns.filter(
            (col) => !col.optional || this.optionalActiveFields[col.name]
        );
    }
}
