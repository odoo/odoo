import { registry } from "@web/core/registry";
import * as numbers from "@point_of_sale/app/utils/numbers";
import { formatCurrency } from "@web/core/currency";

export class ResCurrency extends numbers.AbstractNumbers {
    static pythonModel = "res.currency";

    get config() {
        return this.models["pos.config"].get(odoo.pos_config_id);
    }

    get defaultCurrency() {
        return this.config.company_id.currency_id;
    }

    get precision() {
        return this.rounding;
    }

    get isDefaultCurrency() {
        return this.id === this.defaultCurrency.id;
    }

    rawConvert(amount) {
        return this.isDefaultCurrency ? amount : amount * this.rate;
    }

    rawConvertToDefaultCurrency(amount) {
        return this.isDefaultCurrency ? amount : amount / this.rate;
    }

    convert(amount) {
        return this.round(this.rawConvert(amount));
    }

    convertToDefaultCurrency(amount) {
        return this.defaultCurrency.round(this.rawConvertToDefaultCurrency(amount));
    }

    convertFormatted(amount) {
        return formatCurrency(this.convert(amount), this.id);
    }
}

registry.category("pos_available_models").add(ResCurrency.pythonModel, ResCurrency);
