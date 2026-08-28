import { Component, useProps, t } from "@odoo/owl";

export class OverlayButtons extends Component {
    static template = "html_builder.OverlayButtons";
    props = useProps({
        state: t.object(),
    });

    setup() {
        this.state = this.props.state;
    }
}
