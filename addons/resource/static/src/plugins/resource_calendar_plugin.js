import { Plugin, signal, t, useConfig } from "@odoo/owl";
import { useEnv } from "@web/owl2/utils";

export class ResourceCalendarPlugin extends Plugin {
    newAttendances = signal(false);
    record = useConfig("record", t.record().optional());
    env = useEnv();

    async reload() {
        if (this.record && this.newAttendances()) {
            this.newAttendances.set(false);
            await this.record.load();
        }
    }

    async confirmAttendanceChanges() {
        // Overrides may return false to refuse the change, nothing is written then.
        this.newAttendances.set(true);
        return true;
    }
}
