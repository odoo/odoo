import { Component, useEffect, useProps, signal, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class CarrierRatesLoader extends Component {
    static template = "delivery.carrier_rates_loader";

    props = useProps();
    isLoadingPrices = signal(false);
    carrierListOpen = signal(false);
    reloadedPrices = signal(false);

    setup() {
        this.ormService = useService("orm");
        this.lastWeight = this.props.record.data.total_weight;

        // save to get the resId for the wizard
        if (!this.props.record.resId && this.props.record.save) {
            (this.props.record.save()).then(() => this.loadCarrierRates());
        }

        // recalculate rates if the weight changes
        useEffect(
            () => {
                const currWeight = this.props.record.data.total_weight;
                if (currWeight !== this.lastWeight) {
                    this.loadCarrierRates();
                    this.lastWeight = currWeight;
                }
            }
        )

        onMounted(() => {
            this.carrierInput = document.querySelector('div[name="carrier_id"] input');

            // change signal values on input events
            if (this.carrierInput) {
                this.onCarrierFocus = () => {
                    this.carrierListOpen.set(true);
                    this.reloadedPrices.set(false);
                };
                this.carrierInput.addEventListener("focus", this.onCarrierFocus);

                this.onCarrierBlur = () => { this.carrierListOpen.set(false); };
                this.carrierInput.addEventListener("blur", this.onCarrierBlur);
            }
        })

        onWillUnmount(() => {
            // remove listeners when component is unmounted
            if (this.carrierInput) {
                this.carrierInput.removeEventListener("focus", this.onCarrierFocus);
                this.carrierInput.removeEventListener("blur", this.onCarrierBlur);
            }
        });
    }

    async loadCarrierRates() {
        const wizardId = this.props.record.resId;
        const carrierIds = this.props.record.data.available_carrier_ids._currentIds || [];
        if (!wizardId || !carrierIds.length) {
            return;
        }

        try {
            this.isLoadingPrices.set(true);

            // Make asynchronous calls to calculate the delivery rate for each carrier
            const ratePromises = carrierIds.map(async (carrierId, index) => {
                // Put a small timeout in between requests to not overload the request queue
                await new Promise(resolve => setTimeout(resolve, index * 100));

                const result = await this.ormService.call(
                    "choose.delivery.carrier",
                    "get_wizard_carrier_rate",
                    [wizardId, carrierId]
                );
                return { carrierId, result };
            });

            const rates = await Promise.all(ratePromises);
            const carrierPrices = {};
            for (const rate of rates) {
                carrierPrices[rate.carrierId] = rate.result;
            }

            await this.props.record.update({
                carrier_prices: carrierPrices,
                carrier_prices_dumped: JSON.stringify(carrierPrices),
            });
        } finally {
            this.isLoadingPrices.set(false);
            this.reloadedPrices.set(true);
        }
    }

    onSeeRates(_ev) {
        if (this.carrierInput) {
            this.carrierInput.click();
            this.carrierInput.dispatchEvent(new InputEvent("change", { bubbles: true }));
            this.carrierInput.focus();
        }
    }
}

registry.category("view_widgets").add("delivery_carrier_rates_loader", {
    component: CarrierRatesLoader,
});
