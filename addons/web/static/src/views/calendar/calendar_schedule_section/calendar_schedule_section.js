import { Component, onMounted, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Record } from "@web/model/record";
import { CardRenderer } from "@web/views/card/card_renderer";

export class CalendarScheduleSection extends Component {
    static template = "web.CalendarScheduleSection";
    static components = {
        Record,
        CardRenderer,
    };
    props = useProps({
        model: t.object(),
        editRecord: t.function(),
    });
    rootRef = signal(null, { type: t.ref() });
    collapsed = signal(false, { type: t.boolean });
    setup() {
        onMounted(() => {
            new FullCalendar.Interaction.Draggable(this.rootRef(), {
                itemSelector: ".o_event_to_schedule_draggable",
                eventData: function (el) {
                    return {
                        title: el.dataset.displayName,
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
