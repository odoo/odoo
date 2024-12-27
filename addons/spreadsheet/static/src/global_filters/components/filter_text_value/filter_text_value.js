/** @ts-check */

import { Component } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { fuzzyLookup } from "@web/core/utils/search";

export class TextFilterValue extends Component {
    static template = "spreadsheet.TextFilterValue";
    static props = {
        label: { type: String, optional: true },
        onValueChanged: Function,
        value: { type: String, optional: true },
        options: {
            type: Array,
            element: {
                type: Object,
                shape: { value: String, formattedValue: String },
            },
            optional: true,
        },
    };
    static components = { AutoComplete };

    translate(label) {
        // the filter label is extracted from the spreadsheet json file.
        return _t(label);
    }

    get options() {
        return this.props.options.map((option) => ({
            value: option.value,
            label: option.formattedValue,
        }));
    }

    get sources() {
        return [this.optionsSource];
    }

    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
        };
    }

    filterOptions(name) {
        if (!name) {
            const visibleOptions = this.options.slice(0, 8);
            if (this.options.length - visibleOptions.length > 0) {
                visibleOptions.push({
                    label: _t("Start typing..."),
                    unselectable: true,
                    classList: "o_m2o_start_typing",
                });
            }
            return visibleOptions;
        }
        return fuzzyLookup(name, this.options, (option) => option.value + option.label);
    }

    loadOptionsSource(request) {
        const options = this.filterOptions(request);

        if (!options.length) {
            options.push({
                label: _t("No matching value"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }
        return options;
    }
}
