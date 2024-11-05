import { Component, onWillStart, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";

export class PresetSlotsPopup extends Component {
    static template = "point_of_sale.PresetSlotsPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        getPayload: Function,
    };

    setup() {
        this.pos = usePos();
        this.state = useState({ selectedPresetId: this.pos.get_order().preset_id.id });

        onWillStart(async () => {
            for (const preset of this.timedPresets) {
                await this.pos.syncPresetSlotAvaibility(preset);
            }
        });
    }

    get timedPresets() {
        return this.pos.models["pos.preset"].filter((p) => p.use_timing);
    }

    getSlots(presetId) {
        return this.pos.models["pos.preset"].get(presetId).uiState.availabilities;
    }

    confirm(slot, preset) {
        this.props.getPayload({ slot, presetId: preset.id });
        this.props.close();
    }
}
