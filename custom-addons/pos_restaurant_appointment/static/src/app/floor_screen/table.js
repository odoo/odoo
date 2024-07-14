/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Table } from "@pos_restaurant/app/floor_screen/table";
import { deserializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;

patch(Table.prototype, {
    _futureAppointments(table) {
        return Object.entries(table.appointment_ids || {})
            .map(([_id, appointment]) => {
                const dateTimeStart = deserializeDateTime(appointment.start);
                const dateTimeStop = deserializeDateTime(appointment.stop);

                return {
                    ...appointment,
                    start: dateTimeStart.toFormat("HH:mm"),
                    start_ts: dateTimeStart.ts,
                    stop: dateTimeStop.toFormat("HH:mm"),
                    stop_ts: dateTimeStop.ts,
                    customer_name: appointment.name,
                };
            })
            .filter(
                (appointment) =>
                    appointment.start_ts > DateTime.now() - (appointment.duration / 2) * 3600000
            )
            .sort((a, b) => a.start_ts - b.start_ts);
    },
    get firstAppointment() {
        const firstAppointment = this._futureAppointments(this.props.table)[0];
        return firstAppointment;
    },
    get textStyle() {
        let style = "";
        const table = this.props.table;
        const dateNow = DateTime.now();
        const dateStart = this.firstAppointment.start_ts;
        const rgb = table.floor.background_color
            .substring(4, table.floor.background_color.length - 1)
            .replace(/ /g, "")
            .split(",");
        const light = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255 > 0.5 ? false : true;
        const order = this.pos.orders.find((o) => o.tableId === this.props.table.id);

        if (!order && dateNow > dateStart) {
            style = `color: ${light ? "#FF6767" : "#850000"};`;
        } else {
            style = `color: ${light ? "white" : "black"};`;
        }

        if (dateNow < dateStart) {
            style += `opacity: 0.7;`;
        }

        style += `bottom: -50px;`;
        return style;
    },
    computePosition(index, nbrHorizontal, widthTable) {
        const offsetPos = this.env.position;
        const position = super.computePosition(index, nbrHorizontal, widthTable);
        const lineIdx = Math.floor(index / nbrHorizontal);

        if (offsetPos.offset === undefined) {
            offsetPos.offset = 0;
            offsetPos.offsetLine = {
                0: 0,
            };
        }

        if (this.firstAppointment) {
            offsetPos.offsetLine[lineIdx + 1] = 50 + offsetPos.offsetLine[lineIdx];
        } else if (!offsetPos.offsetLine[lineIdx + 1]) {
            offsetPos.offsetLine[lineIdx + 1] = offsetPos.offsetLine[lineIdx];
        }

        position.position_v += offsetPos.offsetLine[lineIdx];
        return position;
    },
});
