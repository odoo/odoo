/** @ts-check */

import { Component, onWillStart, onWillUpdateProps, useEffect } from "@odoo/owl";
import { useChildRef, useService } from "@web/core/utils/hooks";

import { TagsList } from "@web/core/tags_list/tags_list";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class SelectionFilterValue extends Component {
    static template = "spreadsheet.SelectionFilterValue";
    static components = {
        TagsList,
        AutoComplete,
    };
    static props = {
        resModel: String,
        field: String,
        value: { type: Array, optional: true },
        onValueChanged: Function,
    };
    static defaultProps = {
        value: [],
    };

    setup() {
        this.inputRef = useChildRef();
        useEffect(
            () => {
                if (this.inputRef.el) {
                    // Prevent the user from typing free-text by setting the maxlength to 0
                    this.inputRef.el.setAttribute("maxlength", 0);
                }
            },
            () => [this.inputRef.el]
        );
        this.tags = [];
        this.sources = [];
        this.fields = useService("field");
        onWillStart(() => this._computeTagsAndSources(this.props));
        onWillUpdateProps((nextProps) => this._computeTagsAndSources(nextProps));
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
