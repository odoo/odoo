/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { localization } from "@web/core/l10n/localization";
import { parseDate, formatDate } from "@web/core/l10n/dates";

import { formatMonetary } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

class AccountPaymentPopOver extends Component {}
AccountPaymentPopOver.props = {
    "*": { optional: true },
}
AccountPaymentPopOver.template = "account.AccountPaymentPopOver";

export class AccountPaymentField extends Component {
    static props = { ...standardFieldProps };

    setup() {
        const position = localization.direction === "rtl" ? "bottom" : "left";
        this.popover = usePopover(AccountPaymentPopOver, { position });
        this.orm = useService("orm");
        this.action = useService("action");
    }

    getInfo() {
        const info = this.props.record.data[this.props.name] || {
            content: [],
            outstanding: false,
            title: "",
            move_id: this.props.record.resId,
        };
        for (const [key, value] of Object.entries(info.content)) {
            value.index = key;
            value.amount_formatted = formatMonetary(value.amount, {
                currencyId: value.currency_id,
            });
            if (value.date) {
                // value.date is a string, parse to date and format to the users date format
                value.date = formatDate(parseDate(value.date));
            }
        }
        return {
            lines: info.content,
            outstanding: info.outstanding,
            title: info.title,
            moveId: info.move_id,
        };
    }

    onInfoClick(ev, line) {
        this.popover.open(ev.currentTarget, {
            title: _t("Journal Entry Info"),
            ...line,
            _onRemoveMoveReconcile: this.removeMoveReconcile.bind(this),
            _onOpenMove: this.openMove.bind(this),
        });
    }

    async assignOutstandingCredit(moveId, id) {
        await this.orm.call(this.props.record.resModel, 'js_assign_outstanding_line', [moveId, id], {});
        await this.props.record.model.root.load();
    }

    async removeMoveReconcile(moveId, partialId) {
        this.popover.close();
        await this.orm.call(this.props.record.resModel, 'js_remove_outstanding_partial', [moveId, partialId], {});
        await this.props.record.model.root.load();
    }

    async openMove(moveId) {
        const action = await this.orm.call(this.props.record.resModel, 'action_open_business_doc', [moveId], {});
        this.action.doAction(action);
    }
}
AccountPaymentField.template = "account.AccountPaymentField";

export const accountPaymentField = {
    component: AccountPaymentField,
    supportedTypes: ["char"],
};

registry.category("fields").add("payment", accountPaymentField);
