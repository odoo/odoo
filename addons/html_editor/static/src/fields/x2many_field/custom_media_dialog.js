import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
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
        if (this.state.activeTab == "IMAGES") {
            await this.imageSave({
                attachments: this.selectedMedia[this.state.activeTab],
                superSaveFunction: () => super.save(),
                propsSaveFunction: (attachments) => this.props.imageSave(attachments),
            });
        } else {
            this.props.videoSave(this.selectedMedia[this.state.activeTab]);
        }
        this.props.close();
    }

    async imageSave({ attachments, superSaveFunction, propsSaveFunction }) {
        const preloadedAttachments = attachments.filter((attachment) => attachment.res_model);
        const nonPreloadedAttachments = attachments.filter((attachment) => !attachment.res_model);
        if (nonPreloadedAttachments.length > 0) {
            await superSaveFunction();
            await propsSaveFunction(nonPreloadedAttachments);
        }
        if (preloadedAttachments.length) {
            await propsSaveFunction(preloadedAttachments);
        }
    }
}
