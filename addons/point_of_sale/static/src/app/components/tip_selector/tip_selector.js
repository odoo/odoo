import { Component, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";

export function confirmLargeTip(dialog, { amount, maxPercentage }) {
    let close;
    const confirmed = new Promise((resolve) => {
        close = dialog.add(
            ConfirmationDialog,
            {
                title: _t("Are you sure?"),
                body: _t(
                    "%s is more than %s% of the order's total amount. Are you sure of this tip amount?",
                    amount,
                    maxPercentage
                ),
                confirm: () => resolve(true),
                cancel: () => {},
            },
            { onClose: () => resolve(false) }
        );
    });
    return Object.assign(confirmed, { close });
}

export class TipSelector extends Component {
    static template = "point_of_sale.TipSelector";
    static components = { PriceFormatter };

    props = useProps({
        title: t.string(),
        class: t.string().optional(),
        onBack: t.function().optional(),
        overallAmount: t.string(),
        tipSubText: t.string(),
        percentageTips: t.array(t.object({ percentage: t.string(), amount: t.string() })),
        selectedPercentage: t.string().optional(),
        inputValue: t.or([t.string(), t.number()]),
        currencySymbol: t.string(),
        disabled: t.boolean().optional(),
        onSelect: t.function(),
        onInput: t.function(),
        onNoTip: t.function(),
        onSettle: t.function(),
    });

    get canSettle() {
        return Boolean(this.props.selectedPercentage || this.props.inputValue);
    }
}
