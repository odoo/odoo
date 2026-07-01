/** @odoo-module **/
import {CustomFilterItem} from "@web/search/filter_menu/custom_filter_item";
import {_lt} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

const {DateTime} = luxon; // eslint-disable-line no-undef

patch(CustomFilterItem.prototype, "date_range.CustomFilterItem", {
    setup() {
        this._super(...arguments);
        this.orm = useService("orm");
        this._computeDateRangeOperators();
    },

    async _computeDateRangeOperators() {
        this.date_ranges = {};
        const result = await this.orm.searchRead(
            "date.range",
            [],
            ["name", "type_id", "date_start", "date_end"],
            {}
        );
        result.forEach((range) => {
            const range_type = range.type_id[0];
            if (this.date_ranges[range_type] === undefined) {
                const r = {
                    symbol: "between",
                    description: `${_lt("in")} ${range.type_id[1]}`,
                    date_range: true,
                    date_range_type: range_type,
                };
                var dateExistingOption = this.OPERATORS.date.find(function (option) {
                    return option.date_range_type === r.date_range_type;
                });
                if (!dateExistingOption) {
                    this.OPERATORS.date.push(r);
                }

                var datetimeExistingOption = this.OPERATORS.datetime.find(function (
                    option
                ) {
                    return option.date_range_type === r.date_range_type;
                });
                if (!datetimeExistingOption) {
                    this.OPERATORS.datetime.push(r);
                }
                this.date_ranges[range_type] = [];
            }
            this.date_ranges[range_type].push(range);
        });
    },

    setDefaultValue(condition) {
        const type = this.fields[condition.field].type;
        const operator = this.OPERATORS[this.FIELD_TYPES[type]][condition.operator];
        if (operator.date_range) {
            const default_range = this.date_ranges[operator.date_range_type][0];
            const d_start = DateTime.fromSQL(`${default_range.date_start} 00:00:00`);
            const d_end = DateTime.fromSQL(`${default_range.date_end} 23:59:59`);
            condition.value = [d_start, d_end];
        } else {
            this._super(...arguments);
        }
    },

    onValueChange(condition, ev) {
        const type = this.fields[condition.field].type;
        const operator = this.OPERATORS[this.FIELD_TYPES[type]][condition.operator];
        if (operator.date_range) {
            const eid = parseInt(ev.target.value);
            const ranges = this.date_ranges[operator.date_range_type];
            const range = ranges.find((x) => x.id === eid);
            const d_start = DateTime.fromSQL(`${range.date_start} 00:00:00`);
            const d_end = DateTime.fromSQL(`${range.date_end} 23:59:59`);
            condition.value = [d_start, d_end];
        } else {
            this._super(...arguments);
        }
    },
});
