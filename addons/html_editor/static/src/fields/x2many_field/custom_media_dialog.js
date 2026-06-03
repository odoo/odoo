import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { _t } from "@web/core/l10n/translation";

export class CustomMediaDialog extends MediaDialog {
    static defaultProps = {
        ...MediaDialog.defaultProps,
        extraTabs: [{ id: "VIDEOS", title: _t("Videos"), Component: VideoSelector }],
    };
    async save() {
        if (this.errorMessages[this.activeTab()]) {
            this.notificationService.add(this.errorMessages[this.activeTab()], {
                type: "danger",
            });
            return;
        }
        if (this.activeTab() == "IMAGES") {
            await this.imageSave(this.selectedMedia[this.activeTab()]);
        } else {
            this.props.videoSave(this.selectedMedia[this.activeTab()]);
        }
        this.props.close();
    }

    async imageSave(attachments) {
        const preloadedAttachments = attachments.filter((attachment) => attachment.res_model);
        const nonPreloadedAttachments = attachments.filter((attachment) => !attachment.res_model);
        if (nonPreloadedAttachments.length > 0) {
            await super.save();
            await this.props.imageSave(nonPreloadedAttachments);
        }
        if (preloadedAttachments.length) {
            await this.props.imageSave(preloadedAttachments);
        }
    }
}
