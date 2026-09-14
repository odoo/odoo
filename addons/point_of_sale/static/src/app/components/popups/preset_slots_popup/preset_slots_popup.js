/** @odoo-module native */
import { Component, onWillStart, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { localization } from "@web/core/l10n/localization";
import { luxon } from "@web/core/l10n/luxon";
import { _t } from "@web/core/translation";
import { Dialog } from "@web/ui/dialog";
const { DateTime } = luxon;
const log = makeLogger("pos.popup.preset_slots");

export class PresetSlotsPopup extends Component {
    static template = "point_of_sale.PresetSlotsPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        getPayload: Function,
    };

    setup() {
        useLifecycleLog(log);
        this.pos = usePos();
        this.state = useState({
            selectedPresetId: this.pos.getOrder().preset_id.id,
            selectedDate: (this.pos.getOrder().preset_time || DateTime.now()).toFormat(
                "yyyy-MM-dd",
            ),
        });

        onWillStart(async () => {
            const endSync = log.perf("willStart: sync slot availability");
            const presets = this.timedPresets;
            try {
                await Promise.all(
                    presets.map((preset) => this.pos.syncPresetSlotAvaibility(preset)),
                );
            } finally {
                endSync({ presets: presets.length });
            }
        });
    }

    get timedPresets() {
        return this.pos.models["pos.preset"].filter((p) => p.use_timing);
    }

    getSlotColor(slot, preset) {
        const isSelected = this.isSelected(slot, preset);
        const isFull = slot.isFull;
        const isPast = slot.datetime < DateTime.now();

        if (!isSelected && isFull) {
            return "o_colorlist_item_numpad_color_1";
        }

        return isSelected
            ? "btn-primary"
            : isPast
              ? "btn-secondary"
              : "o_colorlist_item_numpad_color_10";
    }

    isSelected(slot, preset) {
        const order = this.pos.getOrder();
        return (
            order.preset_time?.ts === slot.datetime.ts &&
            order.preset_id?.id === preset.id
        );
    }

    getSlotsForDate(preset, date) {
        const slots = Object.values(preset.availabilities[date]);
        return slots.reduce((acc, slot) => {
            if (!acc[slot.periode]) {
                acc[slot.periode] = [];
            }

            acc[slot.periode].push(slot);
            return acc;
        }, {});
    }

    getPeriodName(period) {
        const periodNames = {
            morning: _t("Morning"),
            lunch: _t("Lunch"),
            afternoon: _t("Afternoon"),
        };

        return periodNames[period];
    }

    formatDate(date) {
        const dateObj = DateTime.fromFormat(date, "yyyy-MM-dd");
        return dateObj.toFormat(localization.dateFormat);
    }

    confirm(slot, preset) {
        log.pipeline("confirm", () => ({
            order: this.pos.getOrder()?.uuid,
            preset: preset.id,
            slot: slot.datetime?.toISO?.(),
            isFull: slot.isFull,
            orders: slot.order_ids?.size,
        }));
        this.props.getPayload({ slot, presetId: preset.id });
        this.props.close();
    }
}
