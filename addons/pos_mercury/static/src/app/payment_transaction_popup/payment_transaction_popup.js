/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _lt } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

export class PaymentTransactionPopup extends AbstractAwaitablePopup {
    static template = "pos_mercury.PaymentTransactionPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        title: _lt("Online Payment"),
        body: "",
        cancelKey: false,
    };

    setup() {
        super.setup();
        this.state = useState({ message: "", confirmButtonIsShown: false });
        this.props.transaction
            .then((data) => {
                if (data.auto_close) {
                    setTimeout(() => {
                        this.confirm();
                    }, 2000);
                } else {
                    this.state.confirmButtonIsShown = true;
                }
                this.state.message = data.message;
            })
            .progress((data) => {
                this.state.message = data.message;
            });
    }
}
