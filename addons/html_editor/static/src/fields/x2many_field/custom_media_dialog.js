import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { renderMedia } from "@html_editor/main/media/media_dialog/media_dialog_utils";
import { _t } from "@web/core/l10n/translation";

export class CustomMediaDialog extends MediaDialog {
    static defaultProps = {
        ...MediaDialog.defaultProps,
        extraTabs: [{ id: "VIDEOS", title: _t("Videos"), Component: VideoSelector }],
    };
    async save() {
        if (this.errorMessages[this.state?.activeTab]) {
            this.notificationService.add(this.errorMessages[this.state.activeTab], {
                type: "danger",
            });
            return;
        }
        await this.preProcessSave();
        if (this.state.activeTab == "IMAGES") {
            await this.imageSave(this.selectedMedia[this.state.activeTab]);
        } else {
            this.props.videoSave(this.selectedMedia[this.state.activeTab]);
        }
        this.props.close();
    }

    async imageSave(attachments) {
        const preloadedAttachments = attachments.filter((attachment) => attachment.res_model);
        const nonPreloadedAttachments = attachments.filter((attachment) => !attachment.res_model);
        if (nonPreloadedAttachments.length > 0) {
            const elements = await renderMedia({
                orm: this.orm,
                activeTab: this.state.activeTab,
                availableTabs: this.tabs,
                oldMediaNode: this.props.media,
                selectedMedia: nonPreloadedAttachments,
                extraClassesToAdd: this.extraClassesToAdd(),
                extraClassesToRemove: this.initialIconClasses,
            });
            const savedAttachments = elements.map((element) => ({
                id: parseInt(element.dataset.attachmentId),
            }));
            await this.props.imageSave(savedAttachments);
        }
        if (preloadedAttachments.length) {
            await this.props.imageSave(preloadedAttachments);
        }
    }
}
