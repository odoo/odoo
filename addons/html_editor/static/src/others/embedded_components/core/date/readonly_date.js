import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { Component, t, useProps } from "@odoo/owl";
const { DateTime } = luxon;

export class ReadonlyEmbeddedDateComponent extends Component {
    static template = "html_editor.ReadonlyEmbeddedDate";
    props = useProps({
        host: t.object(),
        date: t.string(),
        type: t.string(),
    });

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
        const date = DateTime.fromISO(this.date).toLocal();
        return date.toLocaleString(this.DATE_FORMATS[this.props.type]);
    }
}

export const readonlyDateEmbedding = {
    name: "date",
    Component: ReadonlyEmbeddedDateComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
};
