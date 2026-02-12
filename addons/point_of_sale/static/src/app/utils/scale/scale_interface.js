import { _t } from "@web/core/l10n/translation";
import { formatFloat, roundDecimals } from "@web/core/utils/numbers";
import { Reactive } from "@web/core/utils/reactive";

const TARE_TIMEOUT_MS = 3000;

export class ScaleInterface extends Reactive {
    /** @param {import("@point_of_sale/app/services/pos_store").PosStore} pos */
    constructor(pos) {
        super(...arguments);
        this.setup(...arguments);
    }

    /** @param {import("@point_of_sale/app/services/pos_store").PosStore} pos */
    setup(pos) {
        this.pos = pos;
        this.env = pos.env;
        this.lastWeight = null;
        this.weight = 0;
        this.tare = 0;
        this.hardwareTare = false;
        this.tareRequested = false;
        this.errorCallback = null;
    }

    /**
     * Called when the POS is started. If this method returns `true`, this scale
     * will be used and the other `ScaleInterface` implementations won't be called.
     */
    async connectToScale() {
        return false;
    }

    onWeighingStart() {}

    setErrorCallback(callback) {
        this.errorCallback = callback;
    }

    onError(message) {
        this.errorCallback?.(message);
    }

    confirmWeight() {
        this.lastWeight = this.weight;
        return this.netWeight;
    }

    setProduct(product, decimalAccuracy, unitPrice) {
        this.product = {
            name: product.display_name || _t("Unnamed Product"),
            unitOfMeasure: product.product_tmpl_id?.uom_id?.name || "kg",
            decimalAccuracy,
            unitPrice,
        };
    }

    _setWeight(newWeight) {
        this.weight = newWeight;
        this._setTareIfRequested();
        this._clearLastWeightIfValid();
    }

    _setTareIfRequested() {
        if (this.tareRequested) {
            this.tare = this.weight;
            this.tareRequested = false;
        }
    }

    _clearLastWeightIfValid() {
        if (this.lastWeight && this.isWeightValid) {
            this.lastWeight = null;
        }
    }

    requestTare() {
        if (this.isWeightValid) {
            this.tare = this.weight;
        } else {
            this.tareRequested = true;
            setTimeout(() => this._setTareIfRequested(), TARE_TIMEOUT_MS);
        }
    }

    get isWeightValid() {
        return (
            this.product &&
            this.netWeight > 0 &&
            (!this.lastWeight ||
                roundDecimals(this.weight, this.product.decimalAccuracy) !==
                    roundDecimals(this.lastWeight, this.product.decimalAccuracy))
        );
    }

    get tareWeight() {
        if (this.hardwareTare) {
            return 0;
        }
        return this.tare || 0;
    }

    get netWeight() {
        return roundDecimals(this.weight - this.tareWeight, this.product.decimalAccuracy);
    }

    _formatWeight(weight) {
        const weightString = formatFloat(weight, {
            digits: [0, this.product.decimalAccuracy],
        });
        return `${weightString} ${this.product.unitOfMeasure}`;
    }

    get netWeightString() {
        return this._formatWeight(this.netWeight);
    }

    get tareWeightString() {
        if (this.hardwareTare) {
            return "";
        }
        return this._formatWeight(this.tareWeight);
    }

    get grossWeightString() {
        if (this.hardwareTare) {
            return "";
        }
        return this._formatWeight(this.weight);
    }

    get unitPriceString() {
        const priceString = this.env.utils.formatCurrency(this.product.unitPrice);
        return `${priceString} / ${this.product.unitOfMeasure}`;
    }

    get totalPriceString() {
        return this.env.utils.formatCurrency(this.netWeight * this.product.unitPrice);
    }

    // Scale interfaces can override this to display an error status (e.g. over capacity)
    get warningMessage() {
        return "";
    }
}
