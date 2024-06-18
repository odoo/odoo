import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { patch } from "@web/core/utils/patch";


patch(QRPopup.prototype, {
    setup(){
        super.setup(...arguments);
        if (this.props.qrMethodCode == 'id_qr'){
            this._confirm();
        }
    }
})
