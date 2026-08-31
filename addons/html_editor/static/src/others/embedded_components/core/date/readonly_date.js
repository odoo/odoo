/** @odoo-module native */
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { Component } from "@odoo/owl";
import { DateTime } from "@web/core/l10n/luxon";

export class ReadonlyEmbeddedDateComponent extends Component {
    static template = "html_editor.ReadonlyEmbeddedDate";
    static props = {
        host: { type: HTMLElement },
        date: { type: String },
        type: { type: String },
    };

    setup() {
        this.DATE_FORMATS = {
            datetime: DateTime.DATETIME_MED,
            date: DateTime.DATE_FULL,
            time: DateTime.TIME_SIMPLE,
        };
    }

    get date() {
        return this.props.date;
    }

    get formattedDate() {
        return DateTime.fromISO(this.date)
            .toLocal()
            .toLocaleString(this.DATE_FORMATS[this.props.type]);
    }
}

export const readonlyDateEmbedding = {
    name: "date",
    Component: ReadonlyEmbeddedDateComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
};
