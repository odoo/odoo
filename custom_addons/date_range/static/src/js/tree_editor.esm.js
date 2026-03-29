import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import {Select} from "@web/core/tree_editor/tree_editor_components";
import {TreeEditor} from "@web/core/tree_editor/tree_editor";
import {patch} from "@web/core/utils/patch";

function toDateTime(date, type, end) {
    if (type === "date") {
        return date;
    }
    let jsDate = deserializeDate(date);
    if (end) {
        jsDate = luxon.DateTime.fromObject({
            ...jsDate.c,
            hour: 23,
            minute: 59,
            second: 59,
        });
    }
    return serializeDateTime(jsDate);
}

function fromDateTime(date, type) {
    if (type === "date") {
        return date;
    }
    return serializeDate(deserializeDateTime(date));
}

patch(TreeEditor.prototype, {
    setup() {
        super.setup();
    },
    getValueEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const info = super.getValueEditorInfo.apply(this, arguments);
        if (
            fieldDef &&
            (fieldDef.type === "date" || fieldDef.type === "datetime") &&
            node.operator.includes("daterange")
        ) {
            info.component = Select;
        }
        if (typeof this.env.domain !== "undefined") {
            let dateRanges = this.env.domain.dateRanges;
            if (this.update_operator && this.update_operator.split("daterange_")[1]) {
                dateRanges = this.env.domain.dateRanges.filter(
                    (range) =>
                        range.type_id[0] ===
                        Number(this.update_operator.split("daterange_")[1])
                );
            }
            patch(info, {
                extractProps({value, update}) {
                    const props = super.extractProps.apply(this, arguments);
                    if (
                        fieldDef &&
                        (fieldDef.type === "date" || fieldDef.type === "datetime") &&
                        node.operator.includes("daterange")
                    ) {
                        let selected = dateRanges.find(
                            (range) =>
                                range.date_start ===
                                    fromDateTime(value[1], fieldDef.type) &&
                                range.date_end === fromDateTime(value[0], fieldDef.type)
                        );
                        if (!selected) {
                            selected = dateRanges[0];
                            update([
                                toDateTime(selected.date_end, fieldDef.type),
                                toDateTime(selected.date_start, fieldDef.type, true),
                            ]);
                        }

                        return {
                            options: dateRanges.map((dt) => [dt.id, dt.name]),
                            update: (v) => {
                                const range = dateRanges.find((r) => r.id === v);
                                update([
                                    toDateTime(range.date_end, fieldDef.type),
                                    toDateTime(range.date_start, fieldDef.type, true),
                                ]);
                            },
                            value: selected.id,
                        };
                    }

                    return props;
                },
                isSupported(value) {
                    if (node.operator.includes("daterange")) {
                        return Array.isArray(value) && value.length === 2;
                    }
                    return super.isSupported.apply(this, arguments);
                },
            });
        }
        return info;
    },

    getOperatorEditorInfo(node) {
        const info = super.getOperatorEditorInfo(node);
        patch(info, {
            isSupported([operator]) {
                if (node.operator.includes("daterange")) {
                    return (
                        typeof operator === "string" && operator.includes("daterange")
                    );
                }
                return super.isSupported.apply(this, arguments);
            },
        });
        return info;
    },

    updateLeafOperator(node, operator) {
        super.updateLeafOperator.apply(this, arguments);
        this.update_operator = operator;
        const fieldDef = this.getFieldDef(node.path);
        if (typeof this.env.domain !== "undefined") {
            let dateRanges = this.env.domain.dateRanges.filter(
                (range) => range.type_id[0] === Number(operator.split("daterange_")[1])
            );
            if (!dateRanges.length) {
                dateRanges = this.env.domain.dateRanges;
            }
            if (operator.includes("daterange") && dateRanges) {
                node.value = [
                    toDateTime(dateRanges[0].date_end, fieldDef.type),
                    toDateTime(dateRanges[0].date_start, fieldDef.type, true),
                ];
                this.notifyChanges();
            }
        }
    },
});
