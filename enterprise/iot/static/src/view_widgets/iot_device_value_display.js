/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useIotDevice } from '../iot_device_hook';
import { Component, useState } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class IoTDeviceValueDisplay extends Component {
    static template = `iot.IoTDeviceValueDisplay`;
    static props = {...standardWidgetProps};

    setup() {
        super.setup();
        this.state = useState({ value: '' });
        useIotDevice({
            getIotIp: () => this.props.record.data.iot_ip,
            getIdentifier: () => this.props.record.data.identifier,
            onValueChange: (data) => {
                this.state.value = data.value;
            },
        });
    }
}

export const ioTDeviceValueDisplay = {
    component: IoTDeviceValueDisplay,
};
registry.category('view_widgets').add('iot_device_value_display', ioTDeviceValueDisplay);
