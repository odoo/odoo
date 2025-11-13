import { Component } from "@odoo/owl";
import {
    globalFilterDateRegistry,
    getDateGlobalFilterTypes,
} from "@spreadsheet/global_filters/helpers";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

/**
 * This component is used to select a default value for a date filter.
 * It displays a dropdown with predefined date options.
 */
export class DefaultDateValue extends Component {
    static template = "spreadsheet.DefaultDateValue";
    static components = { Dropdown, DropdownItem };
    static props = {
        value: { type: String, optional: true },
        update: Function,
    };

    get currentFormattedValue() {
        return (
            this.dateOptions.find((option) => option.id === this.props.value)?.label ||
            _t("All time")
        );
    }

    get dateOptions() {
        const filterTypes = getDateGlobalFilterTypes().filter((type) => {
            const item = globalFilterDateRegistry.get(type);
            return !item.isFixedPeriod && !item.shouldBeHidden?.(this.env.model.getters);
        });
        const options = filterTypes.map((type, i) => {
            const item = globalFilterDateRegistry.get(type);
            const nextItem = filterTypes[i + 1] && globalFilterDateRegistry.get(filterTypes[i + 1]);
            return {
                id: type,
                label: item.label,
                separator: nextItem && nextItem.category !== item.category,
            };
        });
        options.at(-1).separator = true;
        options.push({ id: undefined, label: _t("All time") });
        return options;
    }
}
