import { BoothRegistration } from "@website_event_booth/interactions/booth_registration";
import { patch } from "@web/core/utils/patch";

/**
 * This class changes the displayed price after selecting the requested booths.
 */
patch(BoothRegistration.prototype, {
    start() {
        super.start();
        this.categoryPrice = this.selectedBoothCategory ? this.selectedBoothCategory.dataset.price : undefined;
    },
    onBoothTypeChange(ev) {
        super.onBoothTypeChange(ev);
        this.categoryPrice = parseFloat(ev.currentTarget.dataset.price);
    },
    onBoothChange(ev) {
        super.onBoothChange(ev);
        const boothCount = this.countSelectedBooths();
        const boothTotalPriceEl = this.el.querySelector(".o_wbooth_booth_total_price");
        boothTotalPriceEl?.classList.toggle("d-none", !boothCount || !this.categoryPrice);
        this.updatePrice(boothCount);
    },
    updatePrice(boothCount) {
        const boothCurrencyEl = this.el.querySelector(".o_wbooth_booth_total_price .oe_currency_value");
        if (boothCurrencyEl) {
            boothCurrencyEl.textContent = `${boothCount * this.categoryPrice}`;
        }
    },
});
