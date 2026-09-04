import { BuilderNumberInput } from "@html_builder/core/building_blocks/builder_number_input";
import { Component, useProps, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { BuilderComponent } from "./builder_component";
import { WithIgnoreItem, builderSelectProps, useBuilderSelect } from "./builder_select";

export class BuilderNumberSelect extends Component {
    static components = {
        Dropdown,
        BuilderComponent,
        WithIgnoreItem,
        BuilderNumberInput,
    };
    static template = "html_builder.BuilderNumberSelect";

    props = useProps({
        ...builderSelectProps,
        default: t.or([t.number(), t.literal(null)]).optional(0),
        unit: t.string().optional(),
        saveUnit: t.string().optional(),
        step: t.number().optional(),
        min: t.number().optional(),
        max: t.number().optional(),
        composable: t.boolean().optional(false),
        applyWithUnit: t.boolean().optional(true),
    });

    setup() {
        Object.assign(this, useBuilderSelect(this.props));
        this.showNumberInput = false;
    }
}
