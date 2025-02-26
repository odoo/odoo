/**
 * Common code between common and year renderer for our calendar.
 */
export function SlotCalendarMixin(rendererClass) {
    return class extends rendererClass {

        /**
         * @override
         */
        convertSlotToEvent(record) {
            const result = {
                ...super.convertRecordToEvent(record),
                id: record.id, // Arbitrary id to avoid duplicated ids.
                editable: false,
            };
            return result;
        }

        /**
         * @override
         * Prevents clicks on the slots if not coming from the slot_picker widget.
         */
        eventClassNames() {
            const classesToAdd = super.eventClassNames(...arguments);
            if (!this.props.model.meta.context.slots_selectable) {
                classesToAdd.push('pe-none');
            }
            return classesToAdd;
        }

        /**
         * @override
         */
        mapRecordsToEvents() {
            return [
                ...Object.values(this.props.model.data.slots).map((r) => this.convertSlotToEvent(r)),
            ];
        }
    };
};
