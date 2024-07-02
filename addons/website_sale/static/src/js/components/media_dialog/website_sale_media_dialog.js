import { MediaDialog, TABS } from '@web_editor/components/media_dialog/media_dialog';

export class MultiMediaDialog extends MediaDialog {
    setup() {
        super.setup();
        this.addTab(TABS.VIDEOS);
    }

    /**
     * @override
     */
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
                this.props.customImageSave(newAttachments);
            }
            if (preloadedAttachments.length) {
                this.props.customImageSave(preloadedAttachments);
            }
        } else {
            this.props.customVideoSave(this.selectedMedia[this.state.activeTab]);
        }
        this.props.close();
    }
}
