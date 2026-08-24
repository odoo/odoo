import { Plugin, signal, t, useConfig } from "@odoo/owl";

export class ResourceCalendarPlugin extends Plugin {
    newAttendances = signal(false);
    record = useConfig("record", t.record().optional());

    async reload() {
        if (this.record && this.newAttendances()) {
            this.newAttendances.set(false);
            await this.record.load();
        }
    }
}
