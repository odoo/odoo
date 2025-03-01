import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { roundPrecision, formatFloat } from "@web/core/utils/numbers";
import { Reactive } from "@web/core/utils/reactive";

const MEASURING_DELAY_MS = 500;
const TARE_TIMEOUT_MS = 3000;

export class PosScaleService extends Reactive {
    constructor(env, deps) {
        super(...arguments);
        this.setup(env, deps);
    }

    setup(env, deps) {
        this.env = env;
        this.hardwareProxy = deps.hardware_proxy;
        this.reset();
    }

    start(errorCallback) {
        this.onError = errorCallback;
        if (!this.isManualMeasurement) {
            this.isMeasuring = true;
            this._readWeightContinuously();
        }
    }

    reset() {
        this.weight = 0;
        this.tare = 0;
        this.tareRequested = false;
        this.loading = false;
        this.isMeasuring = false;
        this.product = null;
        this.onError = null;
    }

    async _readWeightContinuously() {
        if (!this.isMeasuring) {
            return;
        }
        await this.readWeight();
        setTimeout(() => this._readWeightContinuously(), MEASURING_DELAY_MS);
    }

    async _getWeightFromScale() {
        const { weight } = await this.hardwareProxy.message("scale_read");
        return weight;
    }

    async readWeight() {
        this.loading = true;
        try {
            this._checkScaleIsConnected();
            this.weight = await this._getWeightFromScale();
        } catch (error) {
            this.isMeasuring = false;
            this.onError?.(error.message);
        }
        this.loading = false;
        this._setTareIfRequested();
    }

    setProduct(product, unitPrice) {
        this.product = {
            name: product.display_name || _t("Unnamed Product"),
            unitOfMeasure: product.uom_id?.name || "kg",
            rounding: product.uom_id?.rounding || 0.001,
            unitPrice,
        };
    }

    _setTareIfRequested() {
        if (this.tareRequested) {
            this.tare = this.weight;
            this.tareRequested = false;
        }
    }

    requestTare() {
        this.tareRequested = true;
        if (this.isManualMeasurement && !this.loading) {
            this.readWeight();
        } else {
            setTimeout(() => this._setTareIfRequested(), TARE_TIMEOUT_MS);
        }
    }

    get isManualMeasurement() {
        // In Community we don't know anything about the connected scale,
        // so we assume automatic measurement.
        return false;
    }

    get netWeight() {
        return roundPrecision(this.weight - (this.tare || 0), this.product.rounding);
    }

    get netWeightString() {
        const weightString = formatFloat(this.netWeight, {
            digits: [0, this._roundingDecimalPlaces],
        });
        return `${weightString} ${this.product.unitOfMeasure}`;
    }

    get tareWeightString() {
        const weightString = formatFloat(this.tare || 0, {
            digits: [0, this._roundingDecimalPlaces],
        });
        return `${weightString} ${this.product.unitOfMeasure}`;
    }

    get grossWeightString() {
        const weightString = formatFloat(this.weight, { digits: [0, this._roundingDecimalPlaces] });
        return `${weightString} ${this.product.unitOfMeasure}`;
    }

    get unitPriceString() {
        const priceString = this.env.utils.formatCurrency(this.product.unitPrice);
        return `${priceString} / ${this.product.unitOfMeasure}`;
    }

    get totalPriceString() {
        const priceString = this.env.utils.formatCurrency(this.netWeight * this.product.unitPrice);
        return priceString;
    }

    get _roundingDecimalPlaces() {
        return Math.ceil(Math.log(1.0 / this.product.rounding) / Math.log(10));
    }

    _checkScaleIsConnected() {
        if (this.hardwareProxy.connectionInfo.status !== "connected") {
            throw new Error(_t("Cannot weigh product - IoT Box is disconnected"));
        }
        if (this.hardwareProxy.connectionInfo.drivers.scale?.status !== "connected") {
            throw new Error(_t("Cannot weigh product - Scale is not connected to IoT Box"));
        }
    }
}

const posScaleService = {
    dependencies: ["hardware_proxy"],
    start(env, deps) {
        return new PosScaleService(env, deps);
    },
};

registry.category("services").add("pos_scale", posScaleService);
