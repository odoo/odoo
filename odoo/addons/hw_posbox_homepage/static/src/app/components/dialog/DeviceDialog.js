/* global owl */

import useStore from "../../hooks/useStore.js";
import { SingleData } from "../SingleData.js";
import { BootstrapDialog } from "./BootstrapDialog.js";

const { Component, xml, useState } = owl;

export class DeviceDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, SingleData };

    setup() {
        this.store = useStore();
        this.state = useState({
            loading: false,
        });
    }

    onClose() {
        this.state.initialization = [];
        this.state.handlerData = {};
    }

    get devices() {
        // Put blackbox first in the list
        return this.store.base.iot_device_status.sort((a, b) =>
            a.type === "fiscal data module" ? -1 : 1
        );
    }

    static template = xml`
        <BootstrapDialog identifier="'device-list'" btnName="'Show'">
            <t t-set-slot="header">
                Devices list
            </t>
            <t t-set-slot="body">
                <div t-if="this.store.base.iot_device_status.length === 0" class="alert alert-warning fs-6" role="alert">
                    No devices found.
                </div>
                <div>
                    <t t-foreach="devices" t-as="device" t-key="device.identifier">
                        <SingleData name="'Device: ' + device.name.slice(0, 40) +  device.name.length > 40 ? '...' : ''" value="device.type + ' - ' + device.identifier.slice(0, 50) + '...'" style="'secondary'" />
                    </t>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
