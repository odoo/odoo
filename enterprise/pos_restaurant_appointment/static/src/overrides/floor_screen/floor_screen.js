import { patch } from "@web/core/utils/patch";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { useSubEnv } from "@odoo/owl";
import { getMin } from "@point_of_sale/utils";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;

patch(FloorScreen.prototype, {
    setup() {
        super.setup(...arguments);
        useSubEnv({ position: {} });
    },
    async _createTableHelper() {
        const table = await super._createTableHelper(...arguments);
        const appointmentRessource = this.pos.models["appointment.resource"].get(
            table.appointment_resource_id?.id
        );

        if (!appointmentRessource) {
            await this.pos.data.searchRead(
                "appointment.resource",
                [["pos_table_ids", "in", table.id]],
                this.pos.data.fields["appointment.resource"],
                { limit: 1 }
            );
        }

        return table;
    },
    async duplicateTableOrFloor() {
        await super.duplicateTableOrFloor(...arguments);
        if (this.selectedTables.length == 0) {
            const tableWoAppointment = [];

            for (const table of this.activeTables) {
                const appointmentRessource = this.pos.models["appointment.resource"].get(
                    table.appointment_resource_id?.id
                );

                if (!appointmentRessource) {
                    tableWoAppointment.push(table.id);
                }
            }

            if (tableWoAppointment.length > 0) {
                await this.pos.data.searchRead(
                    "appointment.resource",
                    [["pos_table_ids", "in", tableWoAppointment]],
                    this.pos.data.fields["appointment.resource"]
                );
            }
        }
    },
    async createTableFromRaw(table) {
        delete table.appointment_resource_id;
        return super.createTableFromRaw(table);
    },

    getFirstAppointment(table) {
        if (!table.appointment_resource_id) {
            return false;
        }
        const appointments = this.pos.models["calendar.event"].getBy(
            "appointment_resource_ids",
            table.appointment_resource_id.id
        );
        if (!appointments) {
            return false;
        }
        const startOfToday = DateTime.now().set({ hours: 0, minutes: 0, seconds: 0 });
        appointments.map((appointment) => {
            if (
                deserializeDateTime(appointment.start).toFormat("yyyy-MM-dd") <
                DateTime.now().toFormat("yyyy-MM-dd")
            ) {
                appointment.start = serializeDateTime(startOfToday);
            }
        });
        const dt_now = DateTime.now();
        const dt_tomorrow_ts = dt_now
            .plus({ days: 1 })
            .set({ hours: 0, minutes: 0, seconds: 0 }).ts;
        const possible_appointments = appointments.filter((a) => {
            const ts_now = dt_now - (a.duration / 2) * 3600000;
            const dt_ts = deserializeDateTime(a.start).ts;
            return dt_ts > ts_now && dt_ts < dt_tomorrow_ts;
        });
        if (possible_appointments.length === 0) {
            return false;
        }
        return getMin(possible_appointments, {
            criterion: (a) => deserializeDateTime(a.start).ts,
        });
    },
    getFormatedDate(date) {
        return deserializeDateTime(date).toFormat("HH:mm");
    },
    isCustomerLate(table) {
        const dateNow = DateTime.now();
        const dateStart = deserializeDateTime(this.getFirstAppointment(table)?.start).ts;
        return (
            dateNow > dateStart && this.getFirstAppointment(table).appointment_status === "booked"
        );
    },
    appointmentStarted(table) {
        return (
            this.getFirstAppointment(table) &&
            deserializeDateTime(this.getFirstAppointment(table).start).ts < DateTime.now().ts
        );
    },
    onClickAppointment(ev, table) {
        if (!this.pos.isEditMode) {
            ev.stopPropagation();
            return this.pos.editBooking(this.getFirstAppointment(table));
        }
    },
});
