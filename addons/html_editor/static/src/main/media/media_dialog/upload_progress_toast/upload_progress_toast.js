import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

export class ProgressBar extends Component {
    static template = "html_editor.ProgressBar";
    static props = {
        progress: { type: Number, optional: true },
        hasError: { type: Boolean, optional: true },
        uploaded: { type: Boolean, optional: true },
        name: String,
        size: { type: String, optional: true },
        errorMessage: { type: String, optional: true },
    };
    static defaultProps = {
        progress: 0,
        hasError: false,
        uploaded: false,
        size: "",
        errorMessage: "",
    };

    get progress() {
        return Math.round(this.props.progress);
    }
}

export class UploadProgressToast extends Component {
    static template = "html_editor.UploadProgressToast";
    static components = {
        ProgressBar,
    };
    static props = {
        close: Function,
    };

    setup() {
        this.uploadService = useService("upload");
        this.state = useState(this.uploadService.progressToast);
    }
}
