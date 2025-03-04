import { KanbanCoverImageDialog } from "@web/views/kanban/kanban_cover_image_dialog";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(KanbanCoverImageDialog.prototype,{

    async _getAttachments() {
        const attachment = await rpc("/project/controllers/get_attachment", { model: this.props.record.resModel, id: this.props.record.resId });
        return attachment.attachments;
    },

    async setCover() {
        const id = this.state.selectedAttachmentId ? this.state.selectedAttachmentId : false;
        await rpc("/project/controllers/set_attachment",
            {   model: this.props.record.resModel, 
                field: this.props.fieldName, 
                task_id: this.props.record.resId, 
                attachment_id: id 
            });
        await this.props.record.load();
        this.props.close();
    }

});
