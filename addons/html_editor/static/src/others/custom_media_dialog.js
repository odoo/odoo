import { MediaDialog } from "../main/media/media_dialog/media_dialog";

export class CustomMediaDialog extends MediaDialog {
    async save() {
        if (this.errorMessages[this.state?.activeTab]) {
            this.notificationService.add(this.errorMessages[this.state.activeTab], {
                type: "danger",
            });
            return;
        }
        if (this.state.activeTab == "IMAGES") {
            const attachments = this.selectedMedia[this.state.activeTab];
            const preloadedAttachments = attachments.filter((attachment) => attachment.res_model);
            this.selectedMedia[this.state.activeTab] = attachments.filter(
                (attachment) => !preloadedAttachments.includes(attachment)
            );
            if (this.selectedMedia[this.state.activeTab].length > 0) {
                await super.save();
                const newAttachments = this.selectedMedia[this.state.activeTab];
                this.props.imageSave(newAttachments);
            }
            if (preloadedAttachments.length) {
                this.props.imageSave(preloadedAttachments);
            }
        } else {
            this.props.videoSave(this.selectedMedia[this.state.activeTab]);
        }
        this.props.close();
    }
}
