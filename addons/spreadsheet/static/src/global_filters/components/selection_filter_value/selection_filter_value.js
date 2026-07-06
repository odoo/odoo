/** @ts-check */

import { Component, computed, onMounted, signal, t, useProps } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useAsyncComputed, useService } from "@web/core/utils/hooks";

export class SelectionFilterValue extends Component {
    static template = "spreadsheet.SelectionFilterValue";
    static components = {
        BadgeTag,
        AutoComplete,
    };
    props = useProps({
        resModel: t.string(),
        field: t.string(),
        value: t.array().optional([]),
        onValueChanged: t.function(),
        placeholder: t.string().optional(),
    });
    fields = useService("field");

    inputRef = signal.ref();

    fieldData = useAsyncComputed(async () => {
        const { resModel } = this.props;
        return { fields: await this.fields.loadFields(resModel), resModel };
    });
    /**
     * Options of the selection field, or `null` while the fields of the current
     * model are loading (or failed to load).
     *
     * @type {import("@odoo/owl").ReadonlySignal<[string, string][] | null>}
     */
    selection = computed(() => {
        const { field, resModel } = this.props;
        const data = this.fieldData();
        if (data?.resModel !== resModel) {
            return null;
        }
        if (!data.fields[field]) {
            throw new Error(`Field "${field}" not found in model "${resModel}"`);
        }
        return data.fields[field].selection;
    });
    sources = computed(() => {
        const { value } = this.props;
        const selected = new Set(value);
        return [
            {
                options: (this.selection() || [])
                    .filter(([val]) => !selected.has(val))
                    .map(([val, label]) => ({
                        label,
                        onSelect: () => {
                            this.props.onValueChanged([...value, val]);
                        },
                    })),
            },
        ];
    });
    tags = computed(() => {
        const { value } = this.props;
        const labels = Object.fromEntries(this.selection() || []);
        return value.map((val) => ({
            id: val,
            text: labels[val] ?? val,
            onDelete: () => {
                this.props.onValueChanged(value.filter((v) => v !== val));
            },
        }));
    });

    setup() {
        onMounted(() => {
            // Prevent the user from typing free-text by setting the maxlength to 0
            this.inputRef().setAttribute("maxlength", 0);
        });
    }

    get placeholder() {
        return this.tags().length ? "" : this.props.placeholder;
    }
}
