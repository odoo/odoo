import { Plugin } from "@html_editor/plugin";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { proxy } from "@odoo/owl";
import { DateTimePickerPopover } from "@web/core/datetime/datetime_picker_popover";
import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";
const { DateTime } = luxon;

const EMBEDDED_DATE_SELECTOR = 'span[data-embedded="date"]';

export class DatePlugin extends Plugin {
    static id = "date";
    static dependencies = ["history", "overlay", "dom", "embeddedComponents"];

    resources = {
        user_commands: [
            {
                id: "insertDateToday",
                title: _t("Today"),
                description: _t("Insert today's date"),
                icon: "fa-calendar",
                run: () => {
                    this.insertDate(DateTime.now(), "date");
                },
            },
            {
                id: "insertDate",
                title: _t("Date"),
                description: _t("Insert any date"),
                icon: "fa-calendar",
                run: () => {
                    this.openDateTimePicker("date");
                },
            },
            {
                id: "insertTime",
                title: _t("Hour"),
                description: _t("Insert the current time"),
                icon: "fa-calendar",
                run: () => {
                    this.insertDate(DateTime.now(), "time");
                },
            },
            {
                id: "insertDateTime",
                title: _t("Date and Time"),
                description: _t("Insert any date and time"),
                icon: "fa-calendar",
                run: () => {
                    this.openDateTimePicker("datetime");
                },
            },
        ],

        powerbox_categories: withSequence(30, { id: "date", name: _t("Date") }),

        powerbox_items: [
            {
                commandId: "insertDateToday",
                categoryId: "date",
            },
            {
                commandId: "insertTime",
                categoryId: "date",
            },
            {
                commandId: "insertDate",
                categoryId: "date",
            },
            {
                commandId: "insertDateTime",
                categoryId: "date",
            },
        ],

        /** Providers */
        selectors_for_feff_providers: () => EMBEDDED_DATE_SELECTOR,
    };

    setup() {
        this.overlay = this.dependencies.overlay.createOverlay(DateTimePickerPopover, {
            className: "popover mw-100",
        });
    }

    /**
     * @param {"date" | "datetime"} [type="date"]
     */
    openDateTimePicker(type = "date") {
        const pickerProps = proxy({
            value: DateTime.now(), // Default date
            type,
            onSelect: (date) => {
                if (type === "date") {
                    this.insertDate(date, type);
                    this.overlay.close();
                } else {
                    pickerProps.value = date;
                }
            },
        });
        this.overlay.open({
            props: {
                showResetButton: false,
                pickerProps,
                close: () => {
                    this.insertDate(pickerProps.value, type);
                    this.overlay.close();
                },
            },
        });
    }

    /**
     * @param {Object} date - Luxon DateTime instance.
     * @param {"date" | "datetime" | "time"} type
     */
    insertDate(date, type) {
        const dateUTC = date.toUTC().toISO();
        const dateEl = parseHTML(
            this.document,
            renderToString("html_editor.EmbeddedDateBlueprint", {
                embeddedProps: JSON.stringify({ date: dateUTC, type }),
            })
        );

        this.dependencies.dom.insert(dateEl);
        this.dependencies.history.commit();
    }
}
