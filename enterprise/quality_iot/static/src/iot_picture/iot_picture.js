/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { TabletImageField, tabletImageField } from "@quality/tablet_image_field/tablet_image_field";
import { useIotDevice } from '@iot/iot_device_hook';
import { useService } from '@web/core/utils/hooks';

export class TabletImageIoTField extends TabletImageField {
    static template = "quality_iot.TabletImageIoTField";
    static props = {
        ...TabletImageField.props,
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
                _t('Please link the corresponding Quality Control Point to the camera.'), {
                title: _t('Camera configuration error'),
                type: 'warning',
            });
            return;
        }
        if (this.props.record.data.test_type !== 'picture') return;
        this.getIotDevice = useIotDevice({
            getIotIp: () => iotIp,
            getIdentifier: () => identifier,
            onValueChange: (data) => {
                if (data.owner && data.owner === data.session_id) {
                    if (data.image && data.message) {
                        this.notification.add(_t(data.message), { type: 'success' });
                        this.props.record.update({ [this.props.name]: data.image });
                    } else {
                        this.notifyFailure();
                    }
                }
            },
        });
    }
    async onTakePicture(ev) {
        if (!this.getIotDevice) return;

        // Stop propagating so that the FileUploader component won't open the file dialog.
        ev.stopImmediatePropagation();
        ev.preventDefault();
        this.notification.add(_t('Capturing image...'), { type: 'info' });
        try {
            const data = await this.getIotDevice().action({});
            if (data.result !== true) {
                this.notifyFailure();
            }
            return data;
        } catch {
            this.notifyFailure();
        }
    }

    notifyFailure() {
        this.notification.add(_t('Please check if the device is still connected.'), {
            type: 'danger',
            title: _t('Connection to device failed'),
        });
    }
}

export const tabletImageIoTField = {
    ...tabletImageField,
    component: TabletImageIoTField,
    extractProps({ options }) {
        const props = tabletImageField.extractProps(...arguments);
        props.ip_field = options.ip_field;
        props.identifier_field = options.identifier;
        return props;
    },
};

registry.category("fields").add("iot_picture", tabletImageIoTField);
