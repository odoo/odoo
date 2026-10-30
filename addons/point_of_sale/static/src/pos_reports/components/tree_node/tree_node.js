import { Component, useProps, types as t } from "@odoo/owl";
import { usePosReport, SLOT_LINE_NAME } from "../../pos_report_plugin";
import { formatCurrency } from "@web/core/currency";
import { formatFloat } from "@web/core/utils/numbers";

export class TreeNode extends Component {
    static template = "pos_reports.TreeNode";
    static components = { TreeNode };

    props = useProps({
        line: t.object(),
        columns: t.array(t.object()),
        depth: t.number().optional(0),
    });

    setup() {
        this.report = usePosReport();
        this.nameExtensions = this.report.getExtensions(SLOT_LINE_NAME);
    }

    get currentLine() {
        return this.props.line;
    }

    get lineClasses() {
        const classes = [];
        const style = this.currentLine.style;
        if (style === "bold") {
            classes.push("fw-bold");
        }
        if (this.currentLine.foldability === "expanded") {
            classes.push("o_report_unfolded");
        }
        classes.push(`line_level_${this.props.depth}`);
        return classes.join(" ");
    }

    get isFoldable() {
        return this.currentLine.foldability !== "static";
    }

    async toggleFold() {
        if (!this.isFoldable) {
            return;
        }
        await this.report.toggleUnfold(this.currentLine);
    }

    getColumnValue(colId) {
        return this.currentLine.values[colId];
    }

    getFormattedValue(column) {
        const value = this.getColumnValue(column.id);

        if (value === null || value === undefined) {
            return "";
        }

        const currency = this.report.meta().currency || {};
        switch (column.type) {
            case "monetary":
                return formatCurrency(value, currency.id);

            case "float":
                return formatFloat(value, {
                    digits: [69, currency.decimal_places],
                });

            case "integer":
                return formatFloat(value, {
                    digits: [69, 0],
                });

            default:
                return String(value);
        }
    }
}
