/** @ts-check */

import {
    Component,
    onWillStart,
    onWillUpdateProps,
    plugin,
    signal,
    t,
    onMounted,
    useProps,
} from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { FieldPlugin } from "@web/core/field_plugin";

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

    setup() {
        this.inputRef = signal.ref();
        onMounted(() => {
            // Prevent the user from typing free-text by setting the maxlength to 0
            this.inputRef().setAttribute("maxlength", 0);
        });
        this.tags = [];
        this.sources = [];
        this.fields = plugin(FieldPlugin);
        onWillStart(() => this._computeTagsAndSources(this.props));
        onWillUpdateProps((nextProps) => this._computeTagsAndSources(nextProps));
    }

    get placeholder() {
        return this.tags.length ? "" : this.props.placeholder;
    }

    async _computeTagsAndSources(props) {
        const fields = await this.fields.loadFields(props.resModel);
        const field = fields[props.field];
        if (!field) {
            throw new Error(`Field "${props.field}" not found in model "${props.resModel}"`);
        }
        const selection = field.selection;
        this.tags = props.value.map((value) => ({
            id: value,
            text: selection.find((option) => option[0] === value)?.[1] ?? value,
            onDelete: () => {
                props.onValueChanged(props.value.filter((v) => v !== value));
            },
        }));
        const alreadySelected = new Set(props.value);
        this.sources = [
            {
                options: selection
                    .filter((option) => !alreadySelected.has(option[0]))
                    .map(([value, formattedValue]) => ({
                        label: formattedValue,
                        onSelect: () => {
                            props.onValueChanged([...props.value, value]);
                        },
                    })),
            },
        ];
    }
}
