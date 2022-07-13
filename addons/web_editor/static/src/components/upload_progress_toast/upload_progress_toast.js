/** @odoo-module */

const { Component, useEffect, useState } = owl;

export class ProgressBar extends Component {
    get progress() {
        return Math.round(this.props.progress);
    }
}
ProgressBar.template = 'web_editor.ProgressBar';

export class UploadProgressToast extends Component {
    setup() {
        this.state = useState({
            isVisible: false,
            numberOfFiles: 0,
        });

        useEffect((numberOfFiles) => {
            if (numberOfFiles === 0) {
                this.state.isVisible = false;
            }
            if (numberOfFiles > this.state.numberOfFiles) {
                this.state.isVisible = true;
            }
            this.state.numberOfFiles = numberOfFiles;
        }, () => [Object.keys(this.props.files).length]);
    }
}
UploadProgressToast.defaultProps = {
    files: {},
};
UploadProgressToast.template = 'web_editor.UploadProgressToast';
UploadProgressToast.components = {
    ProgressBar
};
