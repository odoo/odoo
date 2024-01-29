import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { ListRenderer } from "@web/views/list/list_renderer";

export class ProjectSharingListRenderer extends ListRenderer {
    processAllColumn() {
        const columns = super.processAllColumn(...arguments);
        if (this.props.list.records.length) {
            const allColumns = [];
            const firstRecord = this.props.list.records[0];
            for (const column of columns) {
                if (
                    column.column_invisible &&
                    !["1", "0", "True", "False"].includes(column.column_invisible)
                ) {
                    column.column_invisible = evaluateBooleanExpr(
                        column.column_invisible,
                        firstRecord.evalContextWithVirtualIds
                    );
                    if (column.column_invisible) {
                        continue;
                    }
                }
                allColumns.push(column);
            }
            return allColumns;
        }
        return columns;
    }
}
