/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";

export class PaymentTransactionPopup extends Component {
    static template = "pos_mercury.PaymentTransactionPopup";
    static components = { Dialog };
    static props = ["title?", "transaction", "close"];
    static defaultProps = {
        title: _t("Online Payment"),
    };

    setup() {
        this.state = useState({ message: "", confirmButtonIsShown: false });
        this.props.transaction
            .then((data) => {
                if (data.auto_close) {
                    setTimeout(() => {
                        this.props.close();
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
