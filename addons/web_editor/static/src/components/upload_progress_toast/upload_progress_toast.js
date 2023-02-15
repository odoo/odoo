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
    progress: Number,
    hasError: Boolean,
    uploaded: Boolean,
    name: String,
    size: String,
    errorMessage: String,
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
