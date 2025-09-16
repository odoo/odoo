import { Component, useState, useEffect } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";

export class PosSelfOrderTopAlert extends Component {
    static template = "pos_self_order.TopAlert";
    static props = {};

    setup() {
        this.router = useService("router");
        this.selfOrder = useSelfOrder();

        this.uiState = useState({ topAlert: "" });
        this.previousRoute = null;

        if (!this.selfOrder.session) {
            this.presetSelectedRoutes = [
                "product_list",
                "product",
                "combo_selection",
                "cart",
                "payment",
                "confirmation",
                "stand_number",
                "orderHistory",
            ];
            this.presetNotSelectedRoutes = ["default", "location"];

            useEffect(
                () => {
                    // Preset not selected yet
                    if (
                        !this.presetNotSelectedRoutes.includes(this.previousRoute) &&
                        this.presetNotSelectedRoutes.includes(this.router.activeSlot)
                    ) {
                        const useTimingPresets = this.selfOrder.models["pos.preset"].filter(
                            (p) => p.use_timing
                        );
                        const closest = { slot: null, preset: null };

                        useTimingPresets.forEach((preset) => {
                            const nextSlot = preset.nextSlotAcrossDays;
                            if (
                                nextSlot &&
                                (!closest.slot || nextSlot.datetime < closest.slot.datetime)
                            ) {
                                closest.slot = nextSlot;
                                closest.preset = preset;
                            }
                        });
                        this.setNextSlotAlert(closest);
                    }

                    // Preset selected
                    else if (
                        !this.presetSelectedRoutes.includes(this.previousRoute) &&
                        this.presetSelectedRoutes.includes(this.router.activeSlot)
                    ) {
                        const preset = this.selfOrder.preset;
                        if (preset && preset.use_timing) {
                            const nextSlot = preset.nextSlotAcrossDays;
                            this.setNextSlotAlert({ slot: nextSlot });
                        } else {
                            this.setClosedAlert();
                        }
                    }

                    this.previousRoute = this.router.activeSlot;
                },
                () => [this.router.activeSlot]
            );
        }
    }

    /**
     * @param {string} message
     */
    set alert(message) {
        if (this.selfOrder.session) {
            message = "";
        } else {
            this.uiState.topAlert = message;
        }
    }

    setClosedAlert() {
        this.alert = `We are currently closed. Ordering is not possible but you can still have a look at the menu!`;
    }

    setNextSlotAlert({ slot, preset } = {}) {
        if (!slot) {
            this.setClosedAlert();
            return;
        }

        const nextSlotDatetime = slot.datetime;
        const localized = nextSlotDatetime.setLocale(slot.datetime.loc.locale);
        const dateString = localized.toLocaleString({
            day: "2-digit",
            month: "2-digit",
            minute: "2-digit",
            hour: "2-digit",
        });

        const presetName = preset ? `(${preset.name})` : "";
        this.alert = `We are currently closed. Next available pickup/delivery: ${dateString} ${presetName}`;
    }
}
