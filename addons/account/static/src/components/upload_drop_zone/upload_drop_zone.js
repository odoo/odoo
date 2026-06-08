import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { Component, props, proxy, t } from "@odoo/owl";

export class UploadDropZone extends Component {
    static template = "account.UploadDropZone";
    props = props({
        visible: t.boolean().optional(),
        hideZone: t.function().optional(() => () => {}),
        dragIcon: t.string().optional(),
        dragText: t.string().optional(),
        dragTitle: t.string().optional(),
        dragCompany: t.string().optional(),
        dragShowCompany: t.boolean().optional(),
        dropZoneTitle: t.string().optional(),
        dropZoneDescription: t.string().optional(),
    });

    setup() {
        this.notificationService = useService("notification");
        this.dashboardState = proxy(this.env.dashboardState || {});
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
