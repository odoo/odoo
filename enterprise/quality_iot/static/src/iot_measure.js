/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { FloatField, floatField } from '@web/views/fields/float/float_field';
import { useIotDevice } from '@iot/iot_device_hook';
import { useService } from '@web/core/utils/hooks';

export class IoTMeasureRealTimeValue extends FloatField {
    static template = 'quality_iot.IoTMeasureRealTimeValue';
    static props = {
        ...FloatField.props,
        ip_field: { type: String },
        identifier_field: { type: String },
    };

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.notification = useService('notification');
        const iotIp = this.props.record.data[this.props.ip_field];
        const identifier = this.props.record.data[this.props.identifier_field];
        if (!iotIp || !identifier) {
            this.notification.add(
                _t('Please link the corresponding Quality Control Point to the measurement device.'), {
                title: _t('Measurement device configuration error'),
                type: 'warning',
            });
            return;
        }
        if (this.props.record.data.test_type !== 'measure') return;

        this.getIotDevice = useIotDevice({
            getIotIp: () => iotIp,
            getIdentifier: () => identifier,
            onValueChange: (data) => this.props.record.update({ [this.props.name]: data.value }),
        });
    }

    async onTakeMeasure() {
        if (!this.getIotDevice) return;

        this.notification.add(_t('Getting measurement...'), { type: 'info' });
        try {
            const data = await this.getIotDevice().action({ action: 'read_once' });
            if (data.result !== true) {
                this.notifyFailure();
            }
            return data;
        } catch {
            this.notifyFailure();
        }
    }
    get hasDevice() {
        return this.props.record.data[this.props.ip_field] != "";
    }

    notifyFailure() {
        this.notification.add(_t('Please check if the device is still connected.'), {
            type: 'danger',
            title: _t('Connection to device failed'),
        });
    }
}

registry.category("fields").add("iot_measure", {
    ...floatField,
    component: IoTMeasureRealTimeValue,
    extractProps({ options }) {
        const props = floatField.extractProps(...arguments);
        props.ip_field = options.ip_field;
        props.identifier_field = options.identifier;
        return props;
    },
});
