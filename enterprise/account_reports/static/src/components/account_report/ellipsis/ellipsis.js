/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

import { AccountReportEllipsisPopover } from "@account_reports/components/account_report/ellipsis/popover/ellipsis_popover";

export class AccountReportEllipsis extends Component {
    static template = "account_reports.AccountReportEllipsis";
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
        if (this.props.name)
            return this.props.name.length > this.props.maxCharacters;

        return false;
    }

    copyEllipsisText() {
        navigator.clipboard.writeText(this.props.name);
        this.notification.add(_t("Text copied"), { type: 'success' });
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
