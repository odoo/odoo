import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { Component, useState } from "@odoo/owl";

export class UploadDropZone extends Component {
    static template = "account.UploadDropZone";
    static props = {
        visible: { type: Boolean, optional: true },
        hideZone: { type: Function, optional: true },
        dragIcon: { type: String, optional: true },
        dragText: { type: String, optional: true },
        dragTitle: { type: String, optional: true },
        dragCompany: { type: String, optional: true },
        dragShowCompany: { type: Boolean, optional: true },
        dropZoneTitle: { type: String, optional: true },
        dropZoneDescription: { type: String, optional: true },
    };
    static defaultProps = {
        hideZone: () => {},
    };

    setup() {
        this.notificationService = useService("notification");
        this.dashboardState = useState(this.env.dashboardState || {});
    }

    onDrop(ev) {
        const selector = '.document_file_uploader.o_input_file';
        // look for the closest uploader Input as it may have a context
        let uploadInput = ev.target.closest('.o_drop_area').parentElement.querySelector(selector) || document.querySelector(selector);
        let files = ev.dataTransfer ? ev.dataTransfer.files : false;
        if (uploadInput && !!files) {
            uploadInput.files = ev.dataTransfer.files;
            uploadInput.dispatchEvent(new Event("change"));
        } else {
            this.notificationService.add(
                _t("Could not upload files"),
                {
                    type: "danger",
                });
        }
        this.props.hideZone();
    }
}
