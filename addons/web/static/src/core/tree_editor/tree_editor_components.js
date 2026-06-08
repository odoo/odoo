import { Component } from "@odoo/owl";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { _t } from "@web/core/l10n/translation";
import { toLocaleDateString } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class Input extends Component {
    static props = ["value", "update", "type?", "placeholder?", "startEmpty?"];
    static template = "web.TreeEditor.Input";

    update(value) {
        const newValue = this.props.type === "number" ? Number(value) : value;
        return this.props.update(newValue);
    }
}

export class Select extends Component {
    static props = ["value", "update", "options", "placeholder?", "addBlankOption?"];
    static template = "web.TreeEditor.Select";

    get selectedTooltip() {
        return this.props.options.find((o) => o[0] === this.props.value)?.[2]?.title || false;
    }

    deserialize(value) {
        return JSON.parse(value);
    }

    serialize(value) {
        return JSON.stringify(value);
    }
}

export class Range extends Component {
    static props = ["value", "update", "editorInfo"];
    static template = "web.TreeEditor.Range";

    update(index, newValue) {
        const result = [...this.props.value];
        result[index] = newValue;
        return this.props.update(result);
    }
}

export class RelativeRange extends Component {
    static props = ["value", "update", "relativeInput", "relativeSelect"];
    static template = "web.TreeEditor.relativeRange";

    static options = [
        ["day", _t("day")],
        ["week", _t("week")],
        ["month", _t("month")],
        ["year", _t("year")],
    ];

    update(index, newValue) {
        const result = [...this.props.value];
        result[index] = newValue;
        return this.props.update(result);
    }
}

export class InRange extends Component {
    static props = [
        "value",
        "update",
        "valueTypeEditorInfo",
        "betweenEditorInfo",
        "relativeEditorInfo",
    ];
    static template = "web.TreeEditor.InRange";
    static get options() {
        const now = DateTime.now();
        const tooltip = (start, end) => `${toLocaleDateString(start)} → ${toLocaleDateString(end)}`;
        return [
            ["today", _t("Today"), { title: toLocaleDateString(now) }],
            ["last7Days", _t("Last 7 days"), { title: tooltip(now.minus({ days: 6 }), now) }],
            ["last30Days", _t("Last 30 days"), { title: tooltip(now.minus({ days: 29 }), now) }],
            ["monthToDate", _t("Month to date"), { title: tooltip(now.startOf("month"), now) }],
            [
                "lastMonth",
                _t("Last month"),
                {
                    title: tooltip(
                        now.minus({ months: 1 }).startOf("month"),
                        now.minus({ months: 1 }).endOf("month")
                    ),
                },
            ],
            ["yearToDate", _t("Year to date"), { title: tooltip(now.startOf("year"), now) }],
            ["last365Days", _t("Last 365 days"), { title: tooltip(now.minus({ days: 364 }), now) }],
            ["dateRange", _t("Date range")],
            ["relativeRange", _t("Relative range"), { debugOnly: true }],
        ];
    }

    updateValueType(newValueType) {
        const [fieldType, currentValueType] = this.props.value;
        if (currentValueType !== newValueType) {
            let values = [false, false];
            if (newValueType === "dateRange") {
                values = this.props.betweenEditorInfo.defaultValue();
            } else if (newValueType === "relativeRange") {
                values = this.props.relativeEditorInfo.defaultValue();
            }
            return this.props.update([fieldType, newValueType, ...values]);
        }
    }
    updateValues(values) {
        const [fieldType, currentValueType] = this.props.value;
        return this.props.update([fieldType, currentValueType, ...values]);
    }
}

export class List extends Component {
    static components = { BadgeTag };
    static props = ["value", "update", "editorInfo"];
    static template = "web.TreeEditor.List";

    get tags() {
        const { isSupported, stringify } = this.props.editorInfo;
        return this.props.value.map((val, index) => ({
            text: stringify(val),
            color: isSupported(val) ? 0 : 2,
            onDelete: () => {
                this.props.update([
                    ...this.props.value.slice(0, index),
                    ...this.props.value.slice(index + 1),
                ]);
            },
        }));
    }

    update(newValue) {
        return this.props.update([...this.props.value, newValue]);
    }
}
