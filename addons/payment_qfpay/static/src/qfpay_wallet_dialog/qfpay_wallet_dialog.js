/* global QFpay */

import { useLayoutEffect } from "@web/owl2/utils";
import { Component, onWillStart, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";

export class QFPayWalletDialog extends Component {
    static components = { Dialog };
    static template = "payment_qfpay.qfpayWalletDialog";

    props = useProps({
        close: t.function(),
        sdkUrl: t.string(),
        sdkEnv: t.string(),
        sdkRegion: t.string(),
        pickerPaymentType: t.string(),
        paymentIntent: t.string(),
        outTradeNo: t.string(),
        txamt: t.string(),
        txcurrcd: t.string(),
        returnUrl: t.string(),
        onPaymentComplete: t.function(),
        onPaymentError: t.function(),
    });

    setup() {
        onWillStart(() => loadJS(this.props.sdkUrl));

        useLayoutEffect(
            () => {
                const qfpayInstance = QFpay.config({
                    region: this.props.sdkRegion,
                    env: this.props.sdkEnv,
                    sessionId: this.props.paymentIntent,
                });
                qfpayInstance.element({ theme: "default" }).createWallet({
                    selector: "#o_qfpay_wallet_dialog_container",
                });
                qfpayInstance
                    .payment()
                    .walletPay(
                        {
                            paysource: "payment_element_checkout",
                            out_trade_no: this.props.outTradeNo,
                            txamt: this.props.txamt,
                            txcurrcd: this.props.txcurrcd,
                            support_pay_type: [this.props.pickerPaymentType],
                        },
                        this.props.paymentIntent
                    );
                qfpayInstance
                    .confirmWalletPayment({ return_url: this.props.returnUrl })
                    .then(this.props.onPaymentComplete, this.props.onPaymentError);
                return () => qfpayInstance.destroy();
            },
            () => []
        );
    }

    get title() {
        return _t("Complete Your Payment");
    }
}
