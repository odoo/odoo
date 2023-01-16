/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { _lt } from "@web/core/l10n/translation";

const { useState } = owl;

export class PaymentTransactionPopup extends AbstractAwaitablePopup {
    static template = "PaymentTransactionPopup";
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
