/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { localization } from "@web/core/l10n/localization";
import { parseDate, formatDate } from "@web/core/l10n/dates";

import { formatMonetary } from "@web/views/fields/formatters";

const { Component, onWillUpdateProps } = owl;

class AccountPaymentPopOver extends Component {}
AccountPaymentPopOver.template = "account.AccountPaymentPopOver";

export class AccountPaymentField extends Component {
    setup() {
        const position = localization.direction === "rtl" ? "bottom" : "left";
        this.popover = usePopover(AccountPaymentPopOver, { position });
        this.orm = useService("orm");
        this.action = useService("action");

        this.formatData(this.props);
        onWillUpdateProps((nextProps) => this.formatData(nextProps));
    }

    formatData(props) {
        const info = props.record.data[props.name] || {
            content: [],
            outstanding: false,
            title: "",
            move_id: this.props.record.data.id,
        };
        for (let [key, value] of Object.entries(info.content)) {
            value.index = key;
            value.amount_formatted = formatMonetary(value.amount, { currencyId: value.currency_id });
            if (value.date) {
                // value.date is a string, parse to date and format to the users date format
                value.date = formatDate(parseDate(value.date));
            }
        }
        this.lines = info.content;
        this.outstanding = info.outstanding;
        this.title = info.title;
        this.move_id = info.move_id;
    }

    onInfoClick(ev, idx) {
        this.popover.open(ev.currentTarget, {
            title: this.env._t("Journal Entry Info"),
            ...this.lines[idx],
            _onRemoveMoveReconcile: this.removeMoveReconcile.bind(this),
            _onOpenMove: this.openMove.bind(this),
        });
    }

    async assignOutstandingCredit(id) {
        await this.orm.call(this.props.record.resModel, 'js_assign_outstanding_line', [this.move_id, id], {});
        await this.props.record.model.root.load();
        this.props.record.model.notify();
    }

    async removeMoveReconcile(moveId, partialId) {
        this.popover.close();
        await this.orm.call(this.props.record.resModel, 'js_remove_outstanding_partial', [moveId, partialId], {});
        await this.props.record.model.root.load();
        this.props.record.model.notify();
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
