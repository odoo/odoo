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
        this.popover = usePopover();
        this.orm = useService("orm");
        this.action = useService("action");

        this.formatData(this.props);
        onWillUpdateProps((nextProps) => this.formatData(nextProps));
    }

    formatData(props) {
        const info = props.value || {
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
        if (this.popoverCloseFn) {
            this.closePopover();
        }
        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            AccountPaymentPopOver,
            {
                title: this.env._t("Journal Entry Info"),
                ...this.lines[idx],
                _onRemoveMoveReconcile: this.removeMoveReconcile.bind(this),
                _onOpenMove: this.openMove.bind(this),
                onClose: this.closePopover,
            },
            {
                position: localization.direction === "rtl" ? "bottom" : "left",
            },
        );
    }

    closePopover() {
        this.popoverCloseFn();
        this.popoverCloseFn = null;
    }

    async assignOutstandingCredit(id) {
        await this.orm.call(this.props.record.resModel, 'js_assign_outstanding_line', [this.move_id, id], {});
        await this.props.record.model.root.load();
        this.props.record.model.notify();
    }

    async removeMoveReconcile(moveId, partialId) {
        this.closePopover();
        await this.orm.call(this.props.record.resModel, 'js_remove_outstanding_partial', [moveId, partialId], {});
        await this.props.record.model.root.load();
        this.props.record.model.notify();
    }

    async openMove(moveId) {
        const action = await this.orm.call(this.props.record.resModel, 'open_move', [moveId], {});
        this.action.doAction(action);
    }
}
AccountPaymentField.template = "account.AccountPaymentField";
AccountPaymentField.supportedTypes = ["char"];

registry.category("fields").add("payment", AccountPaymentField);
