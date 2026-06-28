/* global owl */

import useStore from "../../hooks/store_hook.js";
import { Dialog } from "./dialog.js";

const { Component, signal, xml } = owl;

export class TimeDialog extends Component {
    static components = { Dialog };

    store = useStore();

    odooUptimeSeconds = signal(this.store.base().odoo_uptime_seconds);
    systemUptimeSeconds = signal(this.store.base().system_uptime_seconds);

    setup() {
        setInterval(() => {
            this.odooUptimeSeconds.set(this.odooUptimeSeconds() + 1);
            this.systemUptimeSeconds.set(this.systemUptimeSeconds() + 1);
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
        <Dialog name="'IoT Box Uptime'" btnName="'View Uptime'">
            <t t-set-slot="body">
                <div class="d-flex flex-column gap-4">
                  <div>
                    <h5>Odoo Service</h5>
                    <div>Running for <b t-out="this.secondsToHumanReadable(this.odooUptimeSeconds())"/></div>
                    <div class="text-secondary">Started at <b t-out="this.startDateFromSeconds(this.odooUptimeSeconds())"/></div>
                  </div>
                  <div t-if="this.store.isLinux()">
                    <h5>Operating System</h5>
                    <div>Running for <b t-out="this.secondsToHumanReadable(this.systemUptimeSeconds())"/></div>
                    <div class="text-secondary">Started at <b t-out="this.startDateFromSeconds(this.systemUptimeSeconds())"/></div>
                  </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </Dialog>
    `;
}
