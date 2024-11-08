import { Component, onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";

const { DateTime } = luxon;
export class SlotsPopup extends Component {
    static template = "pos_self_order.SlotsPopup";
    static props = { selectSlot: Function };

    setup() {
        this.selfOrder = useSelfOrder();
        this.state = useState({
            selectedSlot: null,
        });

        onWillStart(async () => {
            await this.selfOrder.syncPresetSlotAvaibility(this.preset);
        });
    }

    setTime() {
        this.props.selectSlot(this.state.selectedSlot);
    }

    close() {
        this.props.selectSlot(null);
    }

    get preset() {
        return this.selfOrder.currentOrder.preset_id;
    }

    get slots() {
        return Object.entries(this.preset.uiState.availabilities).filter(
            (s) => Object.keys(s[1]).length > 0
        );
    }

    get validSelection() {
        return DateTime.fromSQL(this.state.selectedSlot).isValid;
    }
}
