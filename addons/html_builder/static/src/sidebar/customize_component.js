import { Component, useProps, t } from "@odoo/owl";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { Image } from "@html_builder/core/img";

export class CustomizeComponent extends Component {
    static template = "html_builder.CustomizeComponent";
    static components = { Image };
    props = useProps({
        editingElements: t.array(),
        comp: t.function(),
        compProps: t.object(),
    });

    setup() {
        useOptionsSubEnv(() => this.props.editingElements);
    }
}
