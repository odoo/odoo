/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";

const { Component, xml, useState, markup } = owl;

export class LogsDialog extends Component {
    static props = {};
    static components = { BootstrapDialog };

    setup() {
        this.store = useStore();
        this.interval = null;
        this.state = useState({
            logs: "",
        });

        this.getLogs();
    }

    onOpen() {
        this.interval = setInterval(() => {
            this.getLogs();
        }, 1000);
    }

    onClose() {
        clearInterval(this.interval);
    }

    async getLogs() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/iot_logs",
            });
            this.state.logs = data.logs;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    get logs() {
        return markup(this.state.logs);
    }

    static template = xml`
        <BootstrapDialog identifier="'iotlogs-configuration'" btnName="'IOT Logs'" onOpen.bind="onOpen" onClose.bind="onClose">
            <t t-set-slot="header">
                IOT Logs
            </t>
            <t t-set-slot="body">
                <pre t-esc="this.logs"/>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
