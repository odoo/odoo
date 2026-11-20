import { useComponent } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

export function useMailComposerAttachmentsUploader() {
    const uploadingFiles = [];
    const component = useComponent();
    const { model } = component.props.record;
    const attachmentUploadService = useService("mail.attachment_upload");
    const mailStore = useService("mail.store");
    const operations = useX2ManyCrud(() => component.props.record.data["attachment_ids"], true);
    useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) => {
        detail.proms.push(Promise.all(uploadingFiles));
    });

    /** @param {Iterable<File>} files */
    const uploadFiles = async (files) => {
        const { record } = component.props;
        let resIds;
        if (record.resModel === "mail.scheduled.message") {
            resIds = [record.data.res_id.resId];
        } else {
            // composer does not store res_ids past a certain limit, assume active_ids is used
            resIds = record.data.res_ids
                ? JSON.parse(record.data.res_ids)
                : record.context.active_ids;
        }
        // attachments are copied to each record on send: upload them once
        const thread = mailStore["mail.thread"].insert({
            model: record.data.model || record.context.active_model,
            id: resIds[0],
        });
        // an isolated composer keeps the upload pending (garbage collected if the
        // composer is discarded) without pushing it into the chatter composer
        const composer =
            record.context.sync_attachments_to_thread_composer &&
            record.resModel !== "mail.scheduled.message"
                ? thread.composer
                : { attachments: [] };
        for (const file of files) {
            const attachment = await attachmentUploadService.upload(thread, composer, file);
            if (attachment) {
                await operations.saveRecord([attachment.id]);
            }
        }
    };

    /** @param {Iterable<File>} files */
    const doUpload = async (files) => {
        const promise = uploadFiles(files);
        uploadingFiles.push(promise);
        try {
            await promise;
        } finally {
            uploadingFiles.splice(uploadingFiles.indexOf(promise), 1);
        }
    };

    return doUpload;
}
