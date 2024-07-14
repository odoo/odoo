/** @odoo-module **/

import { registry } from '@web/core/registry';
import { DeviceController } from '@iot/device_controller';

export const deliveryIoTNotificationService = {
    dependencies: ['multi_tab', 'bus_service', 'iot_longpolling'],
    start(_, { multi_tab, bus_service, iot_longpolling }) {
        function _printDocuments(identifier, iotIp, documents, iot_idempotent_ids) {
            const iotDevice = new DeviceController(iot_longpolling, { identifier, iot_ip: iotIp });
            for (const [i, document] of documents.entries()) {
                iotDevice.action({ document, 'iot_idempotent_id': iot_idempotent_ids && iot_idempotent_ids[i] });
            }
        }
        bus_service.subscribe("iot_print_documents", ({ documents, iot_device_identifier, iot_idempotent_ids, iot_ip }) => {
            if (multi_tab.isOnMainTab()) {
                _printDocuments(iot_device_identifier, iot_ip, documents, iot_idempotent_ids);
            }
        });
    },
};

registry.category('services').add('delivery_iot_notification_service', deliveryIoTNotificationService);
