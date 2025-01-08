import BoothRegistration from "@website_event_booth/js/booth_register";

/**
 * This class changes the displayed price after selecting the requested booths.
 */
BoothRegistration.include({

    //--------------------------------------------------------------------------
    // Overrides
    //--------------------------------------------------------------------------

    start() {
        return this._super.apply(this, arguments).then(() => {
            this.categoryPrice = this.selectedBoothCategory ? this.selectedBoothCategory.dataset.price : undefined;
        });
    },

    _onChangeBoothType(ev) {
        this.categoryPrice = parseFloat(ev.currentTarget.dataset.price);
        return this._super.apply(this, arguments);
    },

    /**
     * Updates the displayed total price after selecting the requested booths
     * @param boothCount
     * @private
     */
    _updateUiAfterBoothChange(boothCount) {
        this._super.apply(this, arguments);
        const boothTotalPriceEl = this.el.querySelector(".o_wbooth_booth_total_price");
        boothTotalPriceEl?.classList.toggle("d-none", !boothCount || !this.categoryPrice);
        this._updatePrice(boothCount);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _updatePrice(boothsCount) {
        const boothCurrencyEl = this.el.querySelector(".o_wbooth_booth_total_price .oe_currency_value");
        if (boothCurrencyEl) {
            boothCurrencyEl.textContent = `${boothsCount * this.categoryPrice}`;
        }
    },

});
