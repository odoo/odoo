import { useComponent, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export function useMailComposerAttachmentsUploader() {
    const uploadingFiles = [];
    const component = useComponent();
    const { model } = component.props.record;
    useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) => {
        detail.proms.push(Promise.all(uploadingFiles));
    });

    const doUpload = async (promise) => {
        if (uploadingFiles.length === 0) {
            model.bus.trigger("MAIL_COMPOSER_ATTACHMENT_UPLOAD", { isUploading: true });
        }
        uploadingFiles.push(promise);
        try {
            await promise;
        } finally {
            uploadingFiles.splice(uploadingFiles.indexOf(promise), 1);
            if (uploadingFiles.length === 0) {
                model.bus.trigger("MAIL_COMPOSER_ATTACHMENT_UPLOAD", { isUploading: false });
            }
        }
    };

    return doUpload;
}

export function useMailComposerAttachmentsListener() {
    const state = useState({ uploadingSources: 0 });
    const component = useComponent();
    const { model } = component.props.record;
    useBus(model.bus, "MAIL_COMPOSER_ATTACHMENT_UPLOAD", ({ detail }) => {
        state.uploadingSources += detail.isUploading ? 1 : -1;
    });

    return () => state.uploadingSources > 0;
}
