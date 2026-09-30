/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";

const { Component, useState, xml } = owl;

export class TimeDialog extends Component {
    static props = {};
    static components = { BootstrapDialog };

    setup() {
        this.store = useStore();
        this.state = useState({
            odooUptimeSeconds: this.store.base.odoo_uptime_seconds,
            systemUptimeSeconds: this.store.base.system_uptime_seconds,
        });
        setInterval(() => {
            this.state.odooUptimeSeconds += 1;
            this.state.systemUptimeSeconds += 1;
        }, 1000);
    }

    startDateFromSeconds(uptimeInSeconds) {
        const currentTimeMs = new Date().getTime();
        const odooUptimeMs = uptimeInSeconds * 1000;
        return new Date(currentTimeMs - odooUptimeMs).toUTCString();
    }

    secondsToHumanReadable(periodInSeconds) {
        const SECONDS_PER_HOUR = 3600;
        const SECONDS_PER_DAY = SECONDS_PER_HOUR * 24;
        const days = Math.floor(periodInSeconds / SECONDS_PER_DAY);
        periodInSeconds = periodInSeconds % SECONDS_PER_DAY;
        const hours = Math.floor(periodInSeconds / SECONDS_PER_HOUR);
        periodInSeconds = periodInSeconds % SECONDS_PER_HOUR;
        const minutes = Math.floor(periodInSeconds / 60);
        const seconds = Math.floor(periodInSeconds % 60);

        const formatAmount = (amount, name) => `${amount} ${name}${amount === 1 ? "" : "s"}`;
        const timeParts = [
            formatAmount(days, "day"),
            formatAmount(hours, "hour"),
            formatAmount(minutes, "minute"),
            formatAmount(seconds, "second"),
        ];
        return timeParts.join(", ");
    }

    static template = xml`
        <BootstrapDialog identifier="'time-dialog'" btnName="'View Uptime'">
            <t t-set-slot="header">
                IoT Box Uptime
            </t>
            <t t-set-slot="body">
                <div class="d-flex flex-column gap-4">
                  <div>
                    <h5>Odoo Service</h5>
                    <div>Running for <b t-out="secondsToHumanReadable(state.odooUptimeSeconds)"/></div>
                    <div class="text-secondary">Started at <b t-out="startDateFromSeconds(state.odooUptimeSeconds)"/></div>
                  </div>
                  <div t-if="store.isLinux">
                    <h5>Operating System</h5>
                    <div>Running for <b t-out="secondsToHumanReadable(state.systemUptimeSeconds)"/></div>
                    <div class="text-secondary">Started at <b t-out="startDateFromSeconds(state.systemUptimeSeconds)"/></div>
                  </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
