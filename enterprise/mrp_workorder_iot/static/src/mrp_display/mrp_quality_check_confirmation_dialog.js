/** @odoo-module */

import { onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { MrpQualityCheckConfirmationDialog } from "@mrp_workorder/mrp_display/dialog/mrp_quality_check_confirmation_dialog";
import { TabletImageIoTField } from "@quality_iot/iot_picture/iot_picture";
import { IoTMeasureRealTimeValue } from "@quality_iot/iot_measure";
import { DeviceController } from '@iot/device_controller';
import { PedalStatusButton } from './pedal_status_button';

patch(MrpQualityCheckConfirmationDialog, {
   components: {
      ...MrpQualityCheckConfirmationDialog.components,
      TabletImageIoTField,
      IoTMeasureRealTimeValue,
      PedalStatusButton,
   },
});

patch(MrpQualityCheckConfirmationDialog.prototype, {
   setup() {
      super.setup();
      this.deviceControllers = {};
      this.state = useState({
         showPedalStatus: false,
         pedalConnected: false,
      });
      onWillStart(() => {
         const box2device2key2action = {};
         const check = this.props.record.data;
         if (!check.boxes) {
            return;
         }
         const triggers = JSON.parse(check.boxes);
         for (const iot_box_ip in triggers) {
            if (!(iot_box_ip in box2device2key2action)) {
               box2device2key2action[iot_box_ip] = {};
            }
            const device2key2action = box2device2key2action[iot_box_ip];
            for (const [identifier, key, action] of triggers[iot_box_ip]) {
               if (!(identifier in device2key2action)) {
                  device2key2action[identifier] = {};
               }
               device2key2action[identifier][key] = action;
            }
         }
         for (const iot_box_ip in box2device2key2action) {
            const device2key2action = box2device2key2action[iot_box_ip];
            for (const deviceIdentifier in device2key2action) {
               // Show the pedal status button once there is a device controller instantiated.
               this.state.showPedalStatus = true;
               const controller = new DeviceController(this.env.services.iot_longpolling, {
                  identifier: deviceIdentifier,
                  iot_ip: iot_box_ip,
               });
               controller.addListener(this.createOnValueChangeHandler.bind(this, device2key2action[deviceIdentifier]));
               this.deviceControllers[`${iot_box_ip}/${deviceIdentifier}`] = controller;
            }
         }
         return this.takeOwnership();
      });
      onWillUnmount(() => {
         // Stop listening to the iot devices.
         for (const controller of Object.values(this.deviceControllers)) {
            controller.removeListener();
         }
      });
   },
   createOnValueChangeHandler(key2action, data) {
      if (data.owner && data.owner !== data.session_id) {
         this.state.pedalConnected = false;
      } else {
         for (const key in key2action) {
            if (data.value === key) {
               this.barcode.bus.trigger('barcode_scanned', { barcode: `O-BTN.${key2action[key]}` });
            }
         }
      }
   },
   async takeOwnership() {
      this.state.pedalConnected = true;
      for (const controller of Object.values(this.deviceControllers)) {
         await controller.action({})
            .catch(() => {
               this.notification.add(_t("Check IoT Box connection. Try restarting if needed."), {
                  title: _t("Connection failed"),
                  type: "danger",
               });
               this.state.pedalConnected = false;
            });
      }
   },
   get picInfo() {
      return ({ ...super.picInfo, ...{ "ip_field": "ip", "identifier_field": "identifier" } });
   },
   get measureInfo() {
      return ({ ...super.measureInfo, ...{ "ip_field": "ip", "identifier_field": "identifier" } });
   }
});
