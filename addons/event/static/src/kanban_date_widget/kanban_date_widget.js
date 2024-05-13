import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from "@odoo/owl";

const { DateTime } = luxon;

class KanbanDateWidget extends Component {
    static template = "event.KanbanDateWidget";
    static props = standardWidgetProps;

    get dateBegin() {
        return this.props.record.data.date_begin;
    }
    get dateEnd() {
        return this.props.record.data.date_end;
    }

    get areDateEqual() {
        return DateTime.fromISO(this.dateBegin) === DateTime.fromISO(this.dateEnd);
    }

    format(date, format) {
        return DateTime.fromISO(date).toFormat(format);
    }
}

export const kanbanDateWidget = {
    component: KanbanDateWidget,
};

registry.category("view_widgets").add("event_kanban_date", kanbanDateWidget);
