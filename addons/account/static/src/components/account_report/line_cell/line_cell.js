/** @odoo-module native */
import { AccountReportEditPopover } from "@account/components/account_report/line_cell/popover/edit_popover";
import { Component, markup, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";

export class AccountReportLineCell extends Component {
    static template = "account.AccountReportLineCell";
    static props = {
        line: {
            type: Object,
            optional: true,
        },
        cell: Object,
        cellIndex: Number,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.popover = useService("popover");
        this.controller = useState(this.env.controller);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------------------------------------------------
    isNumeric(type) {
        return ["float", "integer", "monetary", "percentage"].includes(type);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Attributes
    // -----------------------------------------------------------------------------------------------------------------
    get cellClasses() {
        if (this.props.cell.comparison_mode) {
            return this.comparisonClasses;
        }

        let classes = "";

        if (this.props.cell.auditable) {
            classes += " auditable";
        }

        if (this.props.cell.figure_type === "date") {
            classes += " date";
        }

        if (this.props.cell.figure_type === "string") {
            classes += " text";
        }

        if (this.isNumeric(this.props.cell.figure_type)) {
            classes += " numeric text-end";

            if (this.props.cell.no_format !== undefined) {
                switch (Math.sign(this.props.cell.no_format)) {
                    case 1:
                        break;
                    case 0:
                        classes += " muted";
                        break;
                    case -1:
                        classes += " text-danger";
                        break;
                }
            }
        }

        if (this.props.cellIndex % 2) {
            classes += " line_cell_odd";
        }

        if (this.props.cell.class) {
            classes += ` ${this.props.cell.class}`;
        }

        return classes;
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Audit
    // -----------------------------------------------------------------------------------------------------------------
    async audit() {
        const auditAction = await this.orm.call(
            "account.report",
            "dispatch_report_action",
            [
                this.controller.options.report_id,
                this.controller.options,
                "action_audit_cell",
                {
                    report_line_id: this.props.cell.report_line_id,
                    expression_label: this.props.cell.expression_label,
                    calling_line_dict_id: this.props.line.id,
                    column_group_key: this.props.cell.column_group_key,
                },
            ],
            {
                context: this.controller.context,
            },
        );
        if (auditAction.help) {
            auditAction.help = markup(auditAction.help);
        }

        return this.action.doAction(auditAction);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Edit Popover
    // -----------------------------------------------------------------------------------------------------------------
    editPopover(ev) {
        const close = () => {
            this.popoverCloseFn();
            this.popoverCloseFn = null;
        };

        if (this.popoverCloseFn) {
            close();
        }

        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            AccountReportEditPopover,
            {
                line_id: this.props.line.id,
                cell: this.props.cell,
                controller: this.controller,
                onClose: close,
            },
            {
                closeOnClickAway: true,
                position: localization.direction === "rtl" ? "bottom" : "left",
            },
        );
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Comparison cell
    // -----------------------------------------------------------------------------------------------------------------
    get comparisonClasses() {
        let classes = "text-end";

        switch (this.props.cell.comparison_mode) {
            case "green":
                classes += " text-success";
                break;
            case "muted":
                classes += " muted";
                break;
            case "red":
                classes += " text-danger";
                break;
        }

        return classes;
    }
}
