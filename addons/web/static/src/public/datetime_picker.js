import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import {
    deserializeDate,
    deserializeDateTime,
    parseDate,
    parseDateTime,
} from "@web/core/l10n/dates";

export class DatetimePicker extends Interaction {
    static selector = "[data-widget='datetime-picker']";

    setup() {
        this.minDate = this.el.dataset.minDate;
        this.maxDate = this.el.dataset.maxDate;
        this.type = this.el.dataset.widgetType || "datetime";
    }

    start() {
        const parseFunction = this.type === "date" ? parseDate : parseDateTime;
        const deserializeFunction = this.type === "date" ? deserializeDate : deserializeDateTime;
        this.registerCleanup(this.services.datetime_picker
            .create({
                target: this.el,
                pickerProps: {
                    type: this.type,
                    minDate: this.minDate && deserializeFunction(this.minDate),
                    maxDate: this.maxDate && deserializeFunction(this.maxDate),
                    value: parseFunction(this.el.value),
                },
            }).enable());
    }
}

registry
    .category("public.interactions")
    .add("web.datetime_picker", DatetimePicker);
