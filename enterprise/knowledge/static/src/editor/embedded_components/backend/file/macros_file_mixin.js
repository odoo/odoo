import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { AttachToMessageMacro, UseAsAttachmentMacro } from "@knowledge/macros/file_macros";

export const MacrosFileMixin = (T, template) => {
    return class extends T {
        static template = template;

        setup() {
            super.setup();
            this.actionService = useService("action");
            this.uiService = useService("ui");
            this.knowledgeCommandsService = useService("knowledgeCommandsService");
            this.macrosServices = {
                action: this.actionService,
                dialog: this.dialogService,
                ui: this.uiService,
            };
            this.targetRecordInfo = this.knowledgeCommandsService.getCommandsRecordInfo();
        }

        /**
         * Callback function called when the user clicks on the "Send as Message" button.
         * The function will execute a macro that will open the last opened form view,
         * compose a new message and attach the associated file to it.
         * @param {Event} ev
         */
        async onClickAttachToMessage(ev) {
            const dataTransfer = new DataTransfer();
            try {
                const response = await window.fetch(this.fileModel.urlRoute);
                const blob = await response.blob();
                const file = new File([blob], this.fileModel.name, {
                    type: blob.type,
                });
                /**
                 * dataTransfer will be used to mimic a drag and drop of
                 * the file in the target record chatter.
                 * @see KnowledgeMacro
                 */
                dataTransfer.items.add(file);
            } catch {
                return;
            }
            const macro = new AttachToMessageMacro({
                targetXmlDoc: this.targetRecordInfo.xmlDoc,
                breadcrumbs: this.targetRecordInfo.breadcrumbs,
                data: {
                    dataTransfer: dataTransfer,
                },
                services: this.macrosServices,
            });
            macro.start();
        }

        /**
         * Callback function called when the user clicks on the "Use As Attachment" button.
         * The function will execute a macro that will open the last opened form view
         * and add the associated file to the attachments of the chatter.
         * @param {Event} ev
         */
        async onClickUseAsAttachment(ev) {
            let attachment;
            try {
                const response = await window.fetch(this.fileModel.urlRoute);
                const blob = await response.blob();
                const dataURL = await getDataURLFromFile(blob);
                attachment = await rpc("/html_editor/attachment/add_data", {
                    name: this.fileModel.name,
                    data: dataURL.split(",")[1],
                    is_image: false,
                    res_id: this.targetRecordInfo.resId,
                    res_model: this.targetRecordInfo.resModel,
                });
            } catch {
                return;
            }
            if (!attachment) {
                return;
            }
            const macro = new UseAsAttachmentMacro({
                targetXmlDoc: this.targetRecordInfo.xmlDoc,
                breadcrumbs: this.targetRecordInfo.breadcrumbs,
                data: null,
                services: this.macrosServices,
            });
            macro.start();
        }
    };
};
