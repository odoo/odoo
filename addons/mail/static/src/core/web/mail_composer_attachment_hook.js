import { useComponent } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export function useMailComposerAttachmentsUploader() {
    const uploadingFiles = [];
    const component = useComponent();
    const { model } = component.props.record;
    useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) => {
        detail.proms.push(Promise.all(uploadingFiles));
    });

    const doUpload = async (promise) => {
        uploadingFiles.push(promise);
        try {
            await promise;
        } finally {
            uploadingFiles.splice(uploadingFiles.indexOf(promise), 1);
        }
    };

    return doUpload;
}
