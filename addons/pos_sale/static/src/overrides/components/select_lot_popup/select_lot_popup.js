import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class SelectLotPopup extends Component {
    static template = "pos_sale.SelectLotPopup";
    static components = { Dialog };
    static props = {
        getPayload: Function,
        availableLots: Array,
        product: Object,
        close: Function,
        line: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            currentInput: "",
            selectedLot:
                this.props.line?.pack_lot_ids.reduce((acc, packLot, idx) => {
                    acc[idx] = { name: packLot.lot_name };
                    return acc;
                }, {}) || {},
        });
    }

    get availableLots() {
        const names = Object.values(this.state.selectedLot).map((l) => l.name);
        return this.props.availableLots.filter((lot) => !names.includes(lot.name));
    }

    get nbrLot() {
        const arr = Object.values(this.state.selectedLot);
        const lotQty = arr.reduce((acc, lot) => acc + lot.product_qty, 0);
        return this.props.line?.qty > lotQty
            ? Array(arr.length + 1)
            : !this.props.line
            ? Array(1)
            : Array(arr.length);
    }

    get dialogTitle() {
        return _t("Lot/Serial Number(s) Required");
    }

    confirm() {
        this.props.getPayload(this.state.selectedLot);
        this.props.close();
    }

    inputFocus(index) {
        const el = document.getElementById(`lot-selection-${index}`);

        if (el) {
            el.classList.remove("d-none");
        }
    }

    inputBlur(index) {
        setTimeout(() => {
            this.state.currentInput = "";
            const el = document.getElementById(`lot-selection-${index}`);

            if (el) {
                el.classList.add("d-none");
            }
        }, 150);
    }

    inputChange(event) {
        this.state.currentInput = event.target.value;
    }
}
