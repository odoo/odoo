import { Plugin } from "@html_editor/plugin";
import { getColorOrClass } from "@html_editor/utils/color";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { getFontSizeOrClass } from "@html_editor/utils/formatting";
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
    static dependencies = ["history", "overlay", "dom", "embeddedComponents", "selection", "color"];

    resources = {
        user_commands: [
            {
                id: "insertDateToday",
                title: _t("Today"),
                description: _t("Insert today's date"),
                icon: "calendar_today",
                run: () => {
                    this.insertDate(DateTime.now(), "date");
                },
            },
            {
                id: "insertDate",
                title: _t("Date"),
                description: _t("Insert any date"),
                icon: "calendar_today",
                run: () => {
                    this.openDateTimePicker("date");
                },
            },
            {
                id: "insertTime",
                title: _t("Hour"),
                description: _t("Insert the current time"),
                icon: "calendar_today",
                run: () => {
                    this.insertDate(DateTime.now(), "time");
                },
            },
            {
                id: "insertDateTime",
                title: _t("Date and Time"),
                description: _t("Insert any date and time"),
                icon: "calendar_today",
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
        color_target_providers: (node) => closestElement(node, EMBEDDED_DATE_SELECTOR),

        /** Overrides */
        apply_color_overrides: this.applyColorToDateNodes.bind(this),

        /** Handlers */
        on_format_applied_handlers: this.onFormatApplied.bind(this),

        /** Predicates */
        is_formattable_node_predicates: (node) => {
            if (node.matches?.(EMBEDDED_DATE_SELECTOR)) {
                return true;
            }
        },
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
            rounding: 1,
            onSelect: (date) => {
                if (type === "date") {
                    this.insertDate(date, type);
                    this.overlay.close();
                } else {
                    pickerProps.value = date;
                }
            },
        });
        this.editable.blur();
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

        this.unsetDateStyles(dateEl.firstChild);
        this.dependencies.dom.insert(dateEl);
        this.dependencies.history.commit();
    }

    /**
     * Unsets the date element's color and font size to inherit them from
     * its parent list item.
     *
     * @param {HTMLElement} dateNode
     */
    unsetDateStyles(dateNode) {
        const selection = this.dependencies.selection.getEditableSelection();
        const listItem = closestElement(selection?.anchorNode, "li");
        if (!listItem) {
            return;
        }

        const hasColor = getColorOrClass(listItem, "color");
        if (hasColor) {
            dateNode.style.color = "unset";
        }

        const hasFontSize = getFontSizeOrClass(listItem);
        if (hasFontSize) {
            dateNode.style.fontSize = "unset";
        }
    }

    applyColorToDateNodes(color, mode, coloredNodes) {
        const dateNodes = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((n) => closestElement(n, EMBEDDED_DATE_SELECTOR))
                .filter(Boolean)
        );
        for (const dateNode of dateNodes) {
            if (color && coloredNodes.has(dateNode)) {
                dateNode.style.color = "unset";
            } else {
                this.dependencies.color.colorElement(dateNode, color, mode);
                coloredNodes.add(dateNode);
            }
        }
    }

    onFormatApplied(node, formatSpec, applyStyle) {
        if (formatSpec.id !== "fontSize" || node.nodeType !== Node.ELEMENT_NODE || !applyStyle) {
            return;
        }
        for (const dateNode of selectElements(node, EMBEDDED_DATE_SELECTOR)) {
            if (dateNode !== node) {
                dateNode.style.fontSize = "unset";
            }
        }
    }
}
