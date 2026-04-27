import { floatCompare } from "@point_of_sale/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloat, roundPrecision } from "@web/core/utils/numbers";
import { Reactive } from "@web/core/utils/reactive";

// This is functionally identical to the base ScaleService with `pos_iot` patch applied.
// Having a separate copy allows us to keep a certified version that will only change
// if absolutely necessary, whilst the base service is free to change.


export class CertifiedScaleService extends Reactive {
    constructor(env, deps) {
        super(...arguments);
        this.setup(env, deps);
    }

    setup(env, deps) {
        this.env = env;
        this.hardwareProxy = deps.hardware_proxy;
        this.lastWeight = null;
        this.weight = 0;
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
        if (this.isMeasuring) {
            this._scaleDevice?.removeListener();
            this._scaleDevice?.action({ action: "stop_reading" });
        }
        this.loading = false;
        this.isMeasuring = false;
        this.product = null;
        this.onError = null;
    }

    confirmWeight() {
        this.lastWeight = this.weight;
        return this.netWeight;
    }

    async readWeight() {
        this.loading = true;
        try {
            this._checkScaleIsConnected();
            this.weight = await this._getWeightFromScale();
            this._clearLastWeightIfValid();
        } catch (error) {
            this.isMeasuring = false;
            this.onError?.(error.message);
        }
        this.loading = false;
    }

    _checkScaleIsConnected() {
        if (this.hardwareProxy.connectionInfo.status !== "connected") {
            throw new Error(_t("Cannot weigh product - IoT Box is disconnected"));
        }
        if (this.hardwareProxy.connectionInfo.drivers.scale?.status !== "connected") {
            throw new Error(_t("Cannot weigh product - Scale is not connected to IoT Box"));
        }
    }

    async _getWeightFromScale() {
        const weightPromise = new Promise((resolve, reject) => {
            this._scaleDevice.addListener((data) => {
                try {
                    resolve(this._handleScaleMessage(data));
                } catch (error) {
                    reject(error);
                }
                this._scaleDevice.removeListener();
            });
        });
        await this._scaleDevice.action({ action: "read_once" });
        return weightPromise;
    }

    _readWeightContinuously() {
        try {
            this._checkScaleIsConnected();
        } catch (error) {
            this.onError?.(error.message);
            this.isMeasuring = false;
            return;
        }

        this._scaleDevice.addListener((data) => {
            try {
                this.weight = this._handleScaleMessage(data);
                this._clearLastWeightIfValid();
            } catch (error) {
                this.onError?.(error.message);
            }
        });
        // The IoT box only sends the weight when it changes, so we
        // manually read to get the initial value.
        this._scaleDevice.action({ action: "read_once" });
        this._scaleDevice.action({ action: "start_reading" });
    }

    _handleScaleMessage(data) {
        if (data.status.status === "error") {
            throw new Error(`Cannot weigh product - ${data.status.message_body}`);
        } else {
            return data.value || data.result || 0;
        }
    }

    setProduct(product, unitPrice) {
        this.product = {
            name: product.display_name || _t("Unnamed Product"),
            unitOfMeasure: product.uom_id?.name || "kg",
            unitOfMeasureId: product.uom_id?.id,
            rounding: product.uom_id?.rounding || 0.001,
            unitPrice,
        };
    }

    _clearLastWeightIfValid() {
        if (this.lastWeight && this.isWeightValid) {
            this.lastWeight = null;
        }
    }

    get isWeightValid() {
        // LNE requires that the weight changes from the previously
        // added value before another product is allowed to be added.
        return (
            (!this.lastWeight ||
                floatCompare(this.weight, this.lastWeight, {
                    decimals: this._roundingDecimalPlaces,
                }) !== 0) &&
            this.netWeight > 0
        );
    }

    get isManualMeasurement() {
        return this._scaleDevice?.manual_measurement;
    }

    get netWeight() {
        return roundPrecision(this.weight, this.product.rounding);
    }

    get netWeightString() {
        const weightString = formatFloat(this.netWeight, {
            digits: [0, this._roundingDecimalPlaces],
        });
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

    get _scaleDevice() {
        return this.hardwareProxy.deviceControllers.scale;
    }

    get _roundingDecimalPlaces() {
        return Math.ceil(Math.log(1.0 / this.product.rounding) / Math.log(10));
    }
}

const posScaleService = {
    dependencies: ["hardware_proxy"],
    start(env, deps) {
        return new CertifiedScaleService(env, deps);
    },
};

registry.category("services").add("pos_scale", posScaleService, { force: true });
