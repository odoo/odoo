/** @odoo-module **/

import { registry } from '@web/core/registry';
import { FloatField, floatField } from '@web/views/fields/float/float_field';
import { useIotDevice } from '@iot/iot_device_hook';

class IoTMeasureRealTimeValue extends FloatField {
    setup() {
        super.setup();
        useIotDevice({
            getIotIp: () => {
                if (this.props.record.data.test_type === 'measure') {
                    return this.props.record.data[this.props.ip_field];
                }
            },
            getIdentifier: () => {
                if (this.props.record.data.test_type === 'measure') {
                    return this.props.record.data[this.props.identifier_field];
                }
            },
            onValueChange: (data) => {
                if (this.env.model.root.isInEdition) {
                    // Only update the value in the record when the record is in edition mode.
                    return this.props.record.update({ [this.props.name]: data.value });
                }
            },
        });
    }
}
IoTMeasureRealTimeValue.props = {
    ...FloatField.props,
    ip_field: { type: String },
    identifier_field: { type: String },
};

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
