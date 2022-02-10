/** @odoo-module */

const { Component, useEffect, useState } = owl;

export class ProgressBar extends Component {}
ProgressBar.template = 'web_editor.ProgressBar';

export class UploadProgressToast extends Component {
    setup() {
        this.state = useState({ hide: false });

        useEffect((numberOfFiles) => {
            if (numberOfFiles) {
                this.state.hide = false;
            }
        }, () => [Object.keys(this.props.files).length]);
    }

    get show() {
        if (!this.props.files || !Object.keys(this.props.files).length) {
            return false;
        }
        return !this.state.hide;
    }
}
UploadProgressToast.defaultProps = {
    files: {},
};
UploadProgressToast.template = 'web_editor.UploadProgressToast';
UploadProgressToast.components = {
    ProgressBar
};
