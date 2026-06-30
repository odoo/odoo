import { props, Component, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class CarrierRatesLoader extends Component {
    static template = "delivery.carrier_rates_loader";

    props = props();

    setup() {
        this.ormService = useService("orm");
        this.lastWeight = this.props.record.data.total_weight;

        // save to get the resId for the wizard
        if (!this.props.record.resId && this.props.record.save) {
            (this.props.record.save()).then(() => this.loadCarrierRates());
        }

        useEffect(
            () => {
                const currWeight = this.props.record.data.total_weight;
                if (currWeight !== this.lastWeight) {
                    this.loadCarrierRates();
                    this.lastWeight = currWeight;
                }
            }
        )
    }

    async loadCarrierRates() {
        const wizardId = this.props.record.resId;
        const carrierIds = this.props.record.data.available_carrier_ids._currentIds || [];
        if (!wizardId || !carrierIds.length) {
            return;
        }

        // Make asynchronous calls to calculate the delivery rate for each carrier
        const ratePromises = carrierIds.map(async (carrierId) => {
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
    }
}

registry.category("view_widgets").add("delivery_carrier_rates_loader", {
    component: CarrierRatesLoader,
});
