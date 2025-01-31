import { Component, onWillStart, useState } from "@odoo/owl";
import { FormRenderer } from "@web/views/form/form_renderer";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { Record } from "@web/model/record";
import { useService } from "@web/core/utils/hooks";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { parseXML } from "@web/core/utils/xml";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { CALENDAR_MODES } from "@web/views/calendar/calendar_modes";

export class CalendarSidePanel extends Component {
    static components = {
        FormRenderer,
        DatePicker: DateTimePicker,
        FilterPanel: CalendarFilterPanel,
        Record,
    };
    static template = "web.CalendarSidePanel";
    static props = ["model", "mode", "setMode", "context?"];
    static defaultProps = {
        context: {},
    };

    setup() {
        this.viewService = useService("view");

        this.CALENDAR_MODES = CALENDAR_MODES;
        this.state = useState({
            isReady: !this.props.model.hasMultiCreate,
        });

        if (this.props.model.hasMultiCreate) {
            onWillStart(() => {
                this.loadMultiCreateView().then(() => {
                    this.state.isReady = true;
                });
            });
        }
    }

    get datePickerProps() {
        return {
            type: "date",
            showWeekNumbers: false,
            maxPrecision: "days",
            daysOfWeekFormat: "narrow",
            onSelect: (date) => {
                let scale = "week";

                if (this.props.model.date.hasSame(date, "day")) {
                    const scales = ["month", "week", "day"];
                    scale = scales[(scales.indexOf(this.props.model.scale) + 1) % scales.length];
                } else {
                    // Check if dates are on the same week
                    // As a.hasSame(b, "week") does not depend on locale and week always starts on Monday,
                    // we are comparing derivated dates instead to take this into account.
                    const currentDate =
                        this.props.model.date.weekday === 7
                            ? this.props.model.date.plus({ day: 1 })
                            : this.props.model.date;
                    const pickedDate = date.weekday === 7 ? date.plus({ day: 1 }) : date;

                    // a.hasSame(b, "week") does not depend on locale and week alway starts on Monday
                    if (currentDate.hasSame(pickedDate, "week")) {
                        scale = "day";
                    }
                }

                this.props.model.load({ scale, date });
            },
            value: this.props.model.date,
        };
    }
    get filterPanelProps() {
        return {
            model: this.props.model,
        };
    }

    get showDatePicker() {
        return this.props.model.showDatePicker && !this.env.isSmall;
    }

    async loadMultiCreateView() {
        const { fields, relatedModels, views } = await this.viewService.loadViews({
            context: {
                ...this.props.context,
                form_view_ref: this.props.model.meta.multiCreateView,
            },
            resModel: this.props.model.resModel,
            views: [[false, "form"]],
        });
        const parser = new FormArchParser();
        const arch = views.form.arch;
        const resModel = this.props.model.resModel;
        this.multiCreateArchInfo = parser.parse(parseXML(arch), relatedModels, resModel);
        const { activeFields } = extractFieldsFromArchInfo(this.multiCreateArchInfo, fields);
        this.multiCreateRecordProps = {
            resModel,
            fields,
            activeFields,
            context: this.props.context,
            hooks: {
                onRootLoaded: this.onMultiCreateRootLoaded.bind(this),
            },
        };
    }

    onMultiCreateRootLoaded(record) {
        this.props.model.data.multiCreateRecord = record;
    }
}
