/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    get partnerInfos() {
        return this.pos.getPartnerCredit(this.props.partner);
    },
});
