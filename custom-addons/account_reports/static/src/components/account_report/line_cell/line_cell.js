/** @odoo-module */

import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";

import { AccountReportCarryoverPopover } from "@account_reports/components/account_report/line_cell/popover/carryover_popover";
import { AccountReportEditPopover } from "@account_reports/components/account_report/line_cell/popover/edit_popover";

import { Component, markup, useState } from "@odoo/owl";

export class AccountReportLineCell extends Component {
    static template = "account_reports.AccountReportLineCell";
    static props = {
        line: {
            type: Object,
            optional: true,
        },
        cell: Object,
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
        return ['float', 'integer', 'monetary', 'percentage'].includes(type);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Attributes
    // -----------------------------------------------------------------------------------------------------------------
    get cellClasses() {
        let classes = "";

        if (this.props.cell.auditable)
            classes += " auditable";

        if (this.props.cell.figure_type === 'date')
            classes += " date";

        if (this.props.cell.figure_type === 'string')
            classes += " text";

        if (this.isNumeric(this.props.cell.figure_type)) {
            classes += " numeric text-end";

            if (this.props.cell.no_format !== undefined)
                switch (Math.sign(this.props.cell.no_format)) {
                    case 1:
                        break;
                    case 0:
                    case -0:
                        classes += " muted";
                        break;
                    case -1:
                        classes += " text-danger";
                        break;
                }
        }

        if (this.props.cell.class)
            classes += ` ${this.props.cell.class}`;

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
            }
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
        }

        if (this.popoverCloseFn)
            close();

        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            AccountReportEditPopover,
            {
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

    //------------------------------------------------------------------------------------------------------------------
    // Carryover popover
    //------------------------------------------------------------------------------------------------------------------
    carryoverPopover(ev) {
        if (this.popoverCloseFn) {
            this.popoverCloseFn();
            this.popoverCloseFn = null;
        }

        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            AccountReportCarryoverPopover,
            {
                carryoverData: JSON.parse(this.props.cell.info_popup_data),
                options: this.controller.options,
                context: this.controller.context,
            },
            {
                closeOnClickAway: true,
                position: localization.direction === "rtl" ? "bottom" : "left",
            },
        );
    }
}
