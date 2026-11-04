import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";

export class ImageDescription extends Component {
    static components = { Dialog };
    static props = {
        getDescription: Function,
        getTooltip: Function,
        updateImageDescription: Function,
        ...toolbarButtonProps,
    };
    static template = "html_editor.ImageDescription";

    setup() {
        this.dialog = useService("dialog");
    }

    openDescriptionDialog() {
        this.dialog.add(ImageDescriptionDialog, {
            description: this.props.getDescription(),
            onConfirm: (description, tooltip) =>
                this.props.updateImageDescription({ description, tooltip }),
            tooltip: this.props.getTooltip(),
        });
    }
}

class ImageDescriptionDialog extends Component {
    static components = { Dialog };
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
    static template = "html_editor.ImageDescriptionDialog";

    setup() {
        this.state = {
            description: this.props.description,
            tooltip: this.props.tooltip,
        };
    }

    onSave() {
        this.props.onConfirm(this.state.description, this.state.tooltip);
        this.props.close();
    }
}
