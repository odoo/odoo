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
        numAction: t.string().optional(),
        numActionParam: t.any().optional(),
        numUnit: t.string().optional(),
        numComposable: t.boolean().optional(false),
    });

    setup() {
        Object.assign(this, useBuilderSelect(this.props));
        this.showNumberInput = false;
    }
}
