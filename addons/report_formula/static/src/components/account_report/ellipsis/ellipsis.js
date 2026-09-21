/** @odoo-module native */
import { AccountReportEllipsisPopover } from "@report_formula/components/account_report/ellipsis/popover/ellipsis_popover";
import { Component, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";

export class AccountReportEllipsis extends Component {
    static template = "report_formula.AccountReportEllipsis";
    static props = {
        name: { type: String, optional: true },
        no_format: { optional: true },
        type: { type: String, optional: true },
        maxCharacters: Number,
    };

    setup() {
        this.popover = useService("popover");
        this.notification = useService("notification");
        this.controller = useState(this.env.controller);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Ellipsis
    //------------------------------------------------------------------------------------------------------------------
    get triggersEllipsis() {
        if (this.props.name) {
            return this.props.name.length > this.props.maxCharacters;
        }

        return false;
    }

    copyEllipsisText() {
        navigator.clipboard.writeText(this.props.name);
        this.notification.add(_t("Text copied"), { type: "success" });
        this.popoverCloseFn();
        this.popoverCloseFn = null;
    }

    showEllipsisPopover(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        if (this.popoverCloseFn) {
            this.popoverCloseFn();
            this.popoverCloseFn = null;
        }

        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            AccountReportEllipsisPopover,
            {
                name: this.props.name,
                copyEllipsisText: this.copyEllipsisText.bind(this),
            },
            {
                closeOnClickAway: true,
                position: localization.direction === "rtl" ? "left" : "right",
            },
        );
    }
}
