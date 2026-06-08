import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, props, proxy, t } from "@odoo/owl";

export class ProgressBar extends Component {
    static template = "html_editor.ProgressBar";
    props = props({
        progress: t.number().optional(0),
        hasError: t.boolean().optional(false),
        uploaded: t.boolean().optional(false),
        name: t.string(),
        size: t.string().optional(""),
        errorMessage: t.string().optional(""),
        mimetype: t.string().optional(""),
        cancelUpload: t.function().optional(() => () => {}),
    });

    get errorMessage() {
        return this.props.errorMessage || _t("File could not be saved");
    }

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
        this.state = proxy(this.uploadService.progressToast);
    }
}
