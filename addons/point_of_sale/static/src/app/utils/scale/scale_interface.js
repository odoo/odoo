import { _t } from "@web/core/l10n/translation";
import { formatFloat, roundDecimals } from "@web/core/utils/numbers";
import { Reactive } from "@web/core/utils/reactive";

export class ScaleInterface extends Reactive {
    /** @param {import("@point_of_sale/app/services/pos_store").PosStore} pos */
    constructor(pos) {
        super(...arguments);

        this.pos = pos;
        this.env = pos.env;
        this.lastWeight = null;
        this.loading = false;
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

    async readWeight() {
        this.loading = true;
        try {
            const newWeight = (await this._readWeight()) ?? this.weight;
            this._setWeight(newWeight);
        } catch (error) {
            this.onError(error.message);
        }
        this.loading = false;
    }

    /**
     * Read the weight from the scale, and return either the new
     * weight, or null if the weight did not change.
     * @returns {Promise<number | null>}
     */
    async _readWeight() {
        throw new Error("Not Implemented");
    }

    /**
     * Return if the current weight is valid. By default this means
     * that it is positive and not equal to the last weight used.
     * Override to provide additional checks.
     * @returns {boolean}
     */
    get isWeightValid() {
        return (
            !!this.product &&
            this.netWeight > 0 &&
            (!this.lastWeight ||
                roundDecimals(this.weight, this.product.decimalAccuracy) !==
                    roundDecimals(this.lastWeight, this.product.decimalAccuracy))
        );
    }

    /** @param {(message: string, isFatalError: boolean) => void} callback */
    setErrorCallback(callback) {
        this.errorCallback = callback;
    }

    /**
     * @param {string} message
     * @param {boolean} [isFatalError]
     */
    onError(message, isFatalError = true) {
        this.errorCallback?.(message, isFatalError);
    }

    confirmWeight() {
        this.lastWeight = this.weight;
        return this.netWeight;
    }

    /**
     * @param {"product.product"} product
     * @param {number} decimalAccuracy
     * @param {number} unitPrice
     */
    setProduct(product, decimalAccuracy, unitPrice) {
        this.product = {
            name: product.display_name || _t("Unnamed Product"),
            unitOfMeasure: product.product_tmpl_id?.uom_id?.name || "kg",
            decimalAccuracy,
            unitPrice,
        };
    }

    /** @param {number} newWeight */
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
            this.readWeight();
        }
    }

    get tareWeight() {
        if (this.hardwareTare) {
            return 0;
        }
        return this.tare || 0;
    }

    /** @returns {number} */
    get netWeight() {
        return roundDecimals(this.weight - this.tareWeight, this.product.decimalAccuracy);
    }

    /** @param {number} weight */
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

    /** @returns {string} */
    get totalPriceString() {
        return this.env.utils.formatCurrency(this.netWeight * this.product.unitPrice);
    }
}
