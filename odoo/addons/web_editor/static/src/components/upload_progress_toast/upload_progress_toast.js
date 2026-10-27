/** @odoo-module */
import { useService } from '@web/core/utils/hooks';

import { Component, useState } from "@odoo/owl";

export class ProgressBar extends Component {
    get progress() {
        return Math.round(this.props.progress);
    }
}
ProgressBar.template = 'web_editor.ProgressBar';
ProgressBar.props = {
    progress: { type: Number, optional: true },
    hasError: { type: Boolean, optional: true },
    uploaded: { type: Boolean, optional: true },
    name: String,
    size: { type: String, optional: true },
    errorMessage: { type: String, optional: true },
};
ProgressBar.defaultProps = {
    progress: 0,
    hasError: false,
    uploaded: false,
    size: "",
    errorMessage: "",
};

export class UploadProgressToast extends Component {
    setup() {
        this.uploadService = useService('upload');

        this.state = useState(this.uploadService.progressToast);
    }
}
UploadProgressToast.template = 'web_editor.UploadProgressToast';
UploadProgressToast.components = {
    ProgressBar
};
UploadProgressToast.props = {
    close: Function,
};
