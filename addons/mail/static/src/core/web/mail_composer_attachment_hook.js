import { useBus } from "@web/core/utils/hooks";

/**
 * @param {import("@web/model/relational_model/relational_model").RelationalModel} model
 *  the model of the composer record: its save waits for the ongoing uploads
 */
export function useMailComposerAttachmentsUploader(model) {
    const uploadingFiles = [];
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
