import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { ReadonlyEmbeddedDateComponent } from "../../core/date/readonly_date";
import { TimePickerPopover } from "@web/core/time_picker/time_picker_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { useRef } from "@web/owl2/utils";
const { DateTime } = luxon;

export class EmbeddedDateComponent extends ReadonlyEmbeddedDateComponent {
    static template = "html_editor.EmbeddedDate";

    setup() {
        super.setup();
        this.state = useEmbeddedState(this.props.host);
        this.ref = useRef("embedded-date");

        if (this.props.type === "time") {
            this.picker = usePopover(TimePickerPopover);
        } else {
            const pickerProps = () => ({
                type: this.props.type,
                value: DateTime.fromISO(this.date).toLocal(),
            });
            this.picker = useDateTimePicker({
                target: "embedded-date",
                onChange: (date) => {
                    this.state.date = date.toUTC().toISO();
                },
                showResetButton: false,
                get pickerProps() {
                    return pickerProps();
                },
            });
        }
    }

    /**
     * @override
     */
    get date() {
        return this.state.date;
    }

    onClick() {
        if (this.props.type === "time") {
            const date = DateTime.fromISO(this.date).toLocal();
            const timeFormat = date.toFormat("HH:mm");
            this.picker.open(this.ref.el, {
                pickerProps: {
                    value: timeFormat,
                    cssClass: "oe_time_picker",
                    onChange: ({ hour, minute }) => {
                        this.state.date = date.set({ hour, minute }).toUTC().toISO();
                        this.picker.close();
                    },
                },
            });
        } else {
            this.picker.open();
        }
    }
}

export const dateEmbedding = {
    name: "date",
    Component: EmbeddedDateComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) => new StateChangeManager(config),
};
