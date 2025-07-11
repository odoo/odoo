import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";

export class ImageDescription extends Component {
    static components = { Dialog };
    static props = {
        ...toolbarButtonProps,
        openImageDescriptionPopover: Function,
    };
    static template = "html_editor.ImageDescription";
}

export class ImageDescriptionPopover extends Component {
    static props = {
        close: Function,
        description: {
            type: String,
            optional: true,
        },
        onConfirm: Function,
        tooltip: {
            type: String,
            optional: true,
        },
    };
    static template = "html_editor.ImageDescriptionPopover";

    setup() {
        this.state = {
            description: this.props.description,
            tooltip: this.props.tooltip,
        };
    }

    onSave() {
        this.props.onConfirm(this.state.description || "", this.state.tooltip || "");
        this.props.close();
    }
}
