import { Component, onMounted, signal, types as t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class CalendarScheduleSection extends Component {
    static template = "web.CalendarScheduleSection";
    static props = {
        model: Object,
        editRecord: Function,
    };
    rootRef = signal(null, { type: t.ref() });
    collapsed = signal(false, { type: t.boolean });
    setup() {
        onMounted(() => {
            new FullCalendar.Interaction.Draggable(this.rootRef(), {
                itemSelector: ".o_event_to_schedule_draggable",
                eventData: function (el) {
                    return {
                        title: el.innerText,
                        id: el.dataset.resId,
                    };
                },
                appendTo: document.body,
            });
        });
    }

    get displayLoadMoreButton() {
        const { eventsToSchedule } = this.props.model.data;
        return eventsToSchedule && eventsToSchedule.records.length < eventsToSchedule.length;
    }

    get toScheduleString() {
        const { eventsToSchedule } = this.props.model.data;
        if (eventsToSchedule.length) {
            return _t("%s to schedule", eventsToSchedule.length);
        }
        return _t("Nothing to schedule");
    }

    openRecord(event) {
        this.props.editRecord({ ...event, title: event.display_name });
    }
}
