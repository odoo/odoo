odoo.define('web.FullCalendarAdapter', function (require) {
    const {
        Component,
        hooks: {
            useRef,
        },
        tags: {
            xml,
        }
    } = owl;

    function adaptFullCalendarEvent(fcEvent) {
        let event = fcEvent;
        if (!moment.isMoment(fcEvent.start)) {
            event = {
                id: fcEvent.id,
                title: fcEvent.title,
                start: moment(fcEvent.start).utcOffset(0, true),
                end: fcEvent.end && moment(fcEvent.end).utcOffset(0, true),
                allDay: fcEvent.allDay,
                color: fcEvent.color,
            };
            if (fcEvent.extendedProps) {
                event = Object.assign({}, event, {
                    r_start: fcEvent.extendedProps.r_start &&
                        moment(fcEvent.extendedProps.r_start).utcOffset(0, true),
                    r_end: fcEvent.extendedProps.r_end &&
                        moment(fcEvent.extendedProps.r_end).utcOffset(0, true),
                    record: fcEvent.extendedProps.record,
                    attendees: fcEvent.extendedProps.attendees,
                });
            }
        }
        return event;
    }

    class FullCalendarAdapter extends Component {
        constructor() {
            super(...arguments);

            this.fullCalendarRef = useRef('fullCalendar');
            this.fullCalendar = null;
        }

        mounted() {
            super.mounted();

            this.fullCalendar = new FullCalendar.Calendar(
                this.fullCalendarRef.el,
                this.props
            );
            this.fullCalendar.render();
            this._update();
        }
        patched() {
            super.patched();

            this.fullCalendar.unselect();
            this._update();
        }
        willUnmount() {
            super.willUnmount();
            this.fullCalendar.destroy();
        }
        _update() {
            if (this.props.defaultView !== this.fullCalendar.view.type) {
                this.fullCalendar.changeView(this.props.defaultView);
            }
            const date = moment(this.props.defaultDate);
            if (!date.isSame(this.fullCalendar.state.currentDate, 'day')) {
                this.fullCalendar.gotoDate(date.toDate());
            } else {
                // this.fullCalendar.gotoDate already renders events when called
                // so render events only when domain changes
                this.fullCalendar.refetchEvents();
            }
        }
    }
    FullCalendarAdapter.template = xml`<div t-ref="fullCalendar"></div>`;

    return {
        adaptFullCalendarEvent,
        FullCalendarAdapter,
    };
});
