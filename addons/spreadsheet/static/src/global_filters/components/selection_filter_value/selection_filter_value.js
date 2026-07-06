/** @ts-check */

import {
    asyncComputed,
    computed,
    Component,
    onWillStart,
    signal,
    t,
    toRaw,
    onMounted,
    useProps,
} from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useService } from "@web/core/utils/hooks";

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
        this.fields = useService("field");
        this.fieldData = asyncComputed(() => {
            this.props.value;
            return this.fields.loadFields(this.props.resModel);
        });

        this.tags = computed(() => {
            this.props.value;
            const field = this.fieldData()[this.props.field];
            if (!field) {
                throw new Error(
                    `Field "${this.props.field}" not found in model "${this.props.resModel}"`
                );
            }
            const selection = field.selection;

            return this.props.value.map((value) => ({
                id: value,
                text: selection.find(([key]) => key === value)?.[1] ?? value,
                onDelete: () => {
                    this.props.onValueChanged(this.props.value.filter((v) => v !== value));
                },
            }));
        });

        this.sources = computed(() => {
            this.props.value;
            const field = this.fieldData()?.[this.props.field];
            if (!field) {
                throw new Error(
                    `Field "${this.props.field}" not found in model "${this.props.resModel}"`
                );
            }
            const selection = field.selection;
            const alreadySelected = new Set(this.props.value);

            return [
                {
                    options: selection
                        .filter(([value]) => !alreadySelected.has(value))
                        .map(([value, formattedValue]) => ({
                            label: formattedValue,
                            onSelect: () => {
                                this.props.onValueChanged([...toRaw(this.props.value), value]);
                            },
                        })),
                },
            ];
        });

        onWillStart(async () => {
            await this.fieldData.currentPromise();
        });
    }

    get placeholder() {
        return this.tags()?.length ? "" : this.props.placeholder;
    }
}
