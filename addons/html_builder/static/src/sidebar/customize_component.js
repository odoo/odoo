import { Component } from "@odoo/owl";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { Img } from "@html_builder/core/img";

export class CustomizeComponent extends Component {
    static template = "html_builder.CustomizeComponent";
    static components = { Img };
    static props = {
        editingElements: { type: Array },
        comp: { type: Function },
        compProps: { type: Object },
    };

    setup() {
        useOptionsSubEnv(() => this.props.editingElements);
    }
}
