import { ScaleInterface } from "@point_of_sale/app/utils/scale/scale_interface";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { WebSerialScale } from "@iot_webserial/web_serial_scale";
import { openWebSerialDevice } from "@iot_webserial/web_serial_device";

export class WebSerialScaleInterface extends ScaleInterface {
    async connectToScale() {
        this.scale = await openWebSerialDevice(WebSerialScale);
        return Boolean(this.scale);
    }

    async _readWeight() {
        const result = await this.scale.readWeight();
        if (result === null && this.errorStatus) {
            this.onError(this.errorStatus, false);
        }
        return result;
    }

    get hardwareTare() {
        return this.scale.tareEnabled;
    }

    get status() {
        return this.scale.status;
    }

    get errorStatus() {
        if (this.status.OVER_CAPACITY) {
            return _t("Scale is over capacity");
        }
        if (this.status.UNDER_ZERO) {
            return _t("Scale is under zero");
        }
        return "";
    }

    get isWeightValid() {
        return super.isWeightValid && !this.status.SCALE_IN_MOTION && !this.errorStatus;
    }
}

registry
    .category("electronic_scales")
    .add("web_serial", WebSerialScaleInterface, { sequence: 100 });
