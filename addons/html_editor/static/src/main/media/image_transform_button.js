import { Component, useState } from "@odoo/owl";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
export class ImageTransformButton extends Component {
    static template = "html_editor.ImageTransformButton";
    static props = {
        id: String,
        icon: String,
        title: String,
        ...toolbarButtonProps,
        activeTitle: String,
        getTransformState: Function,
        handleImageTransformation: Function,
    };

    setup() {
        this.state = useState(this.props.getTransformState());
    }

    onButtonClick() {
        this.props.handleImageTransformation();
    }
}
