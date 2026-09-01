import { MediaDialog, mediaDialogProps } from "@html_editor/main/media/media_dialog/media_dialog";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { renderMedia } from "@html_editor/main/media/media_dialog/media_dialog_utils";
import { _t } from "@web/core/l10n/translation";
import { props, t } from "@odoo/owl";

export class CustomMediaDialog extends MediaDialog {
    props = props({
        ...mediaDialogProps,
        extraTabs: t
            .array(t.object())
            .optional([{ id: "VIDEOS", title: _t("Videos"), Component: VideoSelector }]),
        imageSave: t.function(),
        videoSave: t.function().optional(),
    });
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
            const elements = await renderMedia({
                orm: this.orm,
                activeTab: this.activeTab(),
                availableTabs: this.tabs,
                document: this.props.document,
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
