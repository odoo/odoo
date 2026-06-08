import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";
import { onWillStart, Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef } from "@web/owl2/utils";
import { FileUploader } from "@web/views/fields/file_handler";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Component used to select attachments from account.move.send.wizard
 * it allows selecting from the account.move attachments
 * and adding other attachments from the user computer
 */
export class AccountMoveSendAttachmentsSelector extends Component {
    static template = "account.AccountMoveSendAttachmentsSelector";
    static components = { Dropdown, DropdownItem, FileUploader };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.mailStore = useService("mail.store");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.fileUploadTriggerRef = useRef("fileUploadTrigger");

        onWillStart(async () => {
            const moveAttachments = await this.orm.searchRead(
                "ir.attachment",
                [
                    ["res_id", "=", this.props.record.data.move_id.id],
                    ["res_model", "=", this.props.record.data.model],
                ],
                ["id", "name", "mimetype"]
            );

            this.props.record.update({
                [this.props.name]: this.attachments.concat(
                    moveAttachments.map((attachment) => ({
                        id: attachment.id,
                        name: attachment.name,
                        mimetype: attachment.mimetype,
                        placeholder: false,
                        manual: false,
                        protect_from_deletion: true,
                        skip: true,
                    }))
                ),
            });
        });
    }

    get attachments() {
        return this.props.record.data[this.props.name] || [];
    }

    get dropdownAttachments() {
        return this.attachments.filter((a) => a.skip);
    }

    async onFileUploaded({ name, data, type }) {
        const thread = await this.mailStore["mail.thread"].insert({
            id: this.props.record.data.move_id.id,
            model: this.props.record.data.model,
        });

        const file = new File([dataUrlToBlob(data, type)], name, { type });
        const attachment = await this.attachmentUploadService.upload(thread, thread.composer, file);

        const fileDict = {
            id: attachment.id,
            name: attachment.name,
            mimetype: attachment.mimetype,
            placeholder: false,
            manual: true,
        };
        this.props.record.update({ [this.props.name]: this.attachments.concat([fileDict]) });
    }

    deleteSkip(attachment) {
        delete attachment["skip"];
    }

    triggerFileUpload(condition = true) {
        if (condition) {
            this.fileUploadTriggerRef.el.click();
        }
    }
}

export const accountMoveSendAttachmentsSelector = {
    component: AccountMoveSendAttachmentsSelector,
};

registry
    .category("fields")
    .add("account_move_send_attachments_selector", accountMoveSendAttachmentsSelector);
