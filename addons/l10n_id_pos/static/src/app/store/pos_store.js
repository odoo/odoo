import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";


patch(PosStore.prototype, {
    async verifyQRISStatus(props, silentError=false) {
        let status = await Promise.race([
            new Promise((resolve, reject) => setTimeout(()=>{
                reject("QR code status cannot be retreived due to network connection issue. Please try again.");
            }, 10000)),
            new Promise(async (resolve) => {
                let result = await this.data.call("l10n_id_pos.qr.code.payment", "l10n_id_get_qris_qr_status", [props.qrId])
                if (result){
                    resolve(result.data.qris_status);
                };
            })
        ]).catch((reject) => {
            if (!silentError){
                this.dialog.add(AlertDialog, {
                    title: _t("Fail To Get Status"),
                    body: _t(reject),
                });
            }
        })
        return status == "paid";
    },
    async getQRCodePopupProps(payment, qr){
        let props = await super.getQRCodePopupProps(payment, qr);
        let extraProps;
        if (payment.payment_method_id.qr_code_method == 'id_qr'){
            extraProps = {
                title: _t("QRIS Payment"),
                confirmLabel: _t("Verify Payment"),
                confirm: this.verifyQRISStatus.bind(this, props),
            }
        }
        return {
            ...props,
            ...extraProps,
        };
    },
})
