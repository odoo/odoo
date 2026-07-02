import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { is24HourFormat } from "@web/core/l10n/time";
import { exprToBoolean } from "@web/core/utils/strings";
import { createElement, parseXML } from "@web/core/utils/xml";
import { Card } from "@web/views/card/card";
import { CARD_ATTRIBUTE } from "@web/views/card/card_arch_parser";
import { CardRenderer } from "@web/views/card/card_renderer";
import { getFormattedDateSpan } from "@web/views/calendar/utils";
import { useViewButtons } from "@web/views/view_button/view_button_hook";

import { Component, useRef, useListener } from "@odoo/owl";

export const BODY_ATTRIBUTE = "popover-body";
export const FOOTER_ATTRIBUTE = "popover-footer";
export const HEADER_ATTRIBUTE = "popover-header";

class CalendarCardRenderer extends CardRenderer {
    static template = "web.CalendarCardRenderer";
    static BODY_ATTRIBUTE = BODY_ATTRIBUTE;
    static FOOTER_ATTRIBUTE = FOOTER_ATTRIBUTE;
    static HEADER_ATTRIBUTE = HEADER_ATTRIBUTE;

    setup() {
        super.setup();
        this.showMenu = false;
    }
}

class CalendarCard extends Card {
    static components = { ...Card.components, CardRenderer: CalendarCardRenderer };
    static props = [...Card.props, "afterButtonClicked"];

    setup() {
        super.setup();
        const rootRef = useRef("root");
        useViewButtons(rootRef, {
            reload: () => this.props.afterButtonClicked(),
        });
    }

    get rendererProps() {
        return {
            ...super.rendererProps,
            slots: this.props.slots,
        };
    }
}

export class CalendarCommonPopover extends Component {
    static template = "web.CalendarCommonPopover";
    static defaultFooterButtonsTemplate = "web.CalendarCommonPopover.DefaultFooterButtons";
    static components = { Dialog, CalendarCard };
    static props = [
        "close",
        "model",
        "record",
        "context?",
        "reloadOnClose?",
        "openRecord?",
        "deleteRecord?",
    ];
    static defaultProps = {
        context: {},
        reloadOnClose: () => {},
        openRecord: () => {},
        deleteRecord: () => {},
    };

    setup() {
        this.time = null;
        this.timeDuration = null;
        this.date = null;
        this.dateDuration = null;

        useListener(
            window,
            "pointerdown",
            (e) => {
                if (!e.target.closest(`.fc-event[data-event-id="${this.props.record.id}"]`)) {
                    e.preventDefault();
                }
            },
            { capture: true }
        );

        this.computeDateTimeAndDuration();
        this.cardXmlDoc = this.getCardXmlDoc();

        const footer = this.props.model.meta.popover.templates[FOOTER_ATTRIBUTE];
        this.displayDefaultFooter =
            !footer ||
            (footer.hasAttribute("replace") && !exprToBoolean(footer.getAttribute("replace")));
    }

    get title() {
        return this.props.record.title || "";
    }

    get isEventEditable() {
        return this.props.model.canEdit;
    }

    get isEventDeletable() {
        return this.props.model.canDelete;
    }

    get isEventViewable() {
        return true;
    }

    computeDateTimeAndDuration() {
        const record = this.props.record;
        if (!record) {
            return;
        }
        const { start, end } = record;
        const isSameDay = start.hasSame(end, "day");

        if (!record.isTimeHidden && !record.isAllDay && isSameDay) {
            this.time = this.formatTimeRange(start, end, is24HourFormat() ? "HH:mm" : "hh:mm a");
            this.timeDuration = this.formatTimeDuration(end.diff(start, ["hours", "minutes"]));
        }
        if (!this.props.model.isDateHidden) {
            this.date = this.formatDateRange(start, end);
            this.dateDuration = this.formatDateDuration(start, end);
        }
    }

    formatTimeRange(start, end, timeFormat) {
        return `${start.toFormat(timeFormat)} - ${end.toFormat(timeFormat)}`;
    }

    formatTimeDuration(duration) {
        const formatParts = [];
        if (duration.hours > 0) {
            const hourString = duration.hours === 1 ? _t("hour") : _t("hours");
            formatParts.push(`h '${hourString}'`);
        }
        if (duration.minutes > 0) {
            const minuteStr = duration.minutes === 1 ? _t("minute") : _t("minutes");
            formatParts.push(`m '${minuteStr}'`);
        }
        return duration.toFormat(formatParts.join(", "));
    }

    formatDateRange(start, end) {
        return getFormattedDateSpan(start, end);
    }

    formatDateDuration(start, end) {
        if (!this.props.record.isAllDay || start.hasSame(end, "day")) {
            return null;
        }
        return end
            .plus({ day: 1 })
            .diff(start, "days")
            .toFormat(`d '${_t("days")}'`);
    }

    getCardXmlDoc() {
        const templates = { ...this.props.model.meta.popover.templates };

        if (BODY_ATTRIBUTE in templates) {
            const bodyTemplate = templates[BODY_ATTRIBUTE];
            bodyTemplate.setAttribute("t-name", CARD_ATTRIBUTE);
            templates[CARD_ATTRIBUTE] = bodyTemplate;
            delete templates[BODY_ATTRIBUTE];
        }

        if (!templates[CARD_ATTRIBUTE]) {
            templates[CARD_ATTRIBUTE] = this.getDefaultPopoverBody();
            if (!templates[HEADER_ATTRIBUTE]) {
                templates[HEADER_ATTRIBUTE] = this.getDefaultPopoverHeader();
            }
        }

        const cardXmlDoc = createElement("card");
        const templatesNode = createElement("templates");
        for (const fieldName of this.props.model.meta.popover.fields) {
            templatesNode.appendChild(createElement("field", { name: fieldName }));
        }
        for (const template in templates) {
            templatesNode.appendChild(templates[template]);
        }
        cardXmlDoc.appendChild(templatesNode);
        return cardXmlDoc;
    }

    getDefaultPopoverBody() {
        const items = [];
        if (this.date) {
            const duration = this.dateDuration
                ? ` <small class="fw-bold">${this.dateDuration}</small>`
                : "";
            items.push(`
                <div class="d-flex align-items-baseline gap-2">
                    <i class="fa fa-fw fa-calendar text-400"/>
                    <span class="fw-bold">${this.date}</span>${duration}
                </div>
            `);
        }
        if (this.time) {
            const duration = this.timeDuration
                ? ` <small class="fw-bold">(${this.timeDuration})</small>`
                : "";
            items.push(`
                <div class="d-flex align-items-baseline gap-2">
                    <i class="fa fa-fw fa-clock-o text-400"/>
                    <span class="fw-bold">${this.time}</span>${duration}
                </div>
            `);
        }
        // Retro-compatibility layer: generate a card template from the fields in the arch
        for (const fieldNode of Object.values(this.props.model.meta.popover.fieldNodes)) {
            if (["1", "True"].includes(fieldNode.invisible)) {
                items.push(`<field name="${fieldNode.name}" invisible="1"/>`);
                continue;
            }
            const widget = `widget="${fieldNode.widget || fieldNode.type}"`;
            const options = `options='${JSON.stringify(fieldNode.options)}'`;
            const readonly = fieldNode.readonly ? `readonly="${fieldNode.readonly}"` : "";
            const field = `<field name="${fieldNode.name}" ${options} ${widget} ${readonly}/>`;
            let label = "";
            if (!fieldNode.options.noLabel && fieldNode.type !== "properties") {
                label = fieldNode.options.icon
                    ? `<i class="${fieldNode.options.icon} text-400" title="${fieldNode.string}"/>`
                    : `<span class="fw-bold">${fieldNode.string}</span>`;
            }
            const invisible = fieldNode.invisible ? `invisible="${fieldNode.invisible}"` : "";
            items.push(
                `<div class="d-flex align-items-baseline gap-2" ${invisible}>${label}${field}</div>`
            );
        }
        return parseXML(`<t t-name="${CARD_ATTRIBUTE}" class="gap-3">${items.join("")}</t>`);
    }

    getDefaultPopoverHeader() {
        return parseXML(`<t t-name="${HEADER_ATTRIBUTE}"><field name="display_name"/></t>`);
    }

    get cardProps() {
        const { fields, resModel } = this.props.model.meta;
        return {
            card: this.cardXmlDoc,
            context: this.props.context,
            fields,
            resModel,
            resId: this.props.record.id,
            readonly: !this.isEventEditable,
            afterButtonClicked: () => {
                this.props.reloadOnClose();
                this.props.close();
            },
            hooks: {
                onRecordSaved: this.props.reloadOnClose,
            },
        };
    }

    onEditEvent() {
        this.props.openRecord();
        this.props.close();
    }

    onDeleteEvent() {
        this.props.deleteRecord();
        this.props.close();
    }
}
