import { Component } from "@odoo/owl";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { _t } from "@web/core/l10n/translation";

export class Input extends Component {
    static props = ["value", "update", "placeholder?", "startEmpty?"];
    static template = "web.TreeEditor.Input";
}

export class Select extends Component {
    static props = ["value", "update", "options", "placeholder?", "addBlankOption?"];
    static template = "web.TreeEditor.Select";

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

export class InRange extends Component {
    static props = ["value", "update", "valueTypeEditorInfo", "betweenEditorInfo"];
    static template = "web.TreeEditor.InRange";
    static options = [
        ["today", _t("Today")],
        ["last7Days", _t("Last 7 days")],
        ["last30Days", _t("Last 30 days")],
        ["monthToDate", _t("Month to date")],
        ["lastMonth", _t("Last month")],
        ["yearToDate", _t("Year to date")],
        ["last365Days", _t("Last 365 days")],
        ["dateRange", _t("Date range")],
    ];
    updateValueType(newValueType) {
        const [fieldType, currentValueType] = this.props.value;
        if (currentValueType !== newValueType) {
            const values =
                newValueType === "dateRange"
                    ? this.props.betweenEditorInfo.defaultValue()
                    : [false, false];
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
