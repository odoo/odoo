import { MediaDialog, TABS } from "@html_editor/main/media/media_dialog/media_dialog";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(MediaDialog.prototype, {
    setup() {
        super.setup();
        this.unsplashService = useService("unsplash");
    },

    async save() {
        const selectedImages = this.selectedMedia[TABS.IMAGES.id];
        if (selectedImages) {
            const unsplashRecords = selectedImages.filter(
                (media) => media.mediaType === "unsplashRecord"
            );
            if (unsplashRecords.length) {
                await this.unsplashService.uploadUnsplashRecords(
                    unsplashRecords,
                    { resModel: this.props.resModel, resId: this.props.resId },
                    (attachments) => {
                        this.selectedMedia[TABS.IMAGES.id] = this.selectedMedia[
                            TABS.IMAGES.id
                        ].filter((media) => media.mediaType !== "unsplashRecord");
                        this.selectedMedia[TABS.IMAGES.id] = this.selectedMedia[
                            TABS.IMAGES.id
                        ].concat(
                            attachments.map((attachment) => ({
                                ...attachment,
                                mediaType: "attachment",
                            }))
                        );
                    }
                );
            }
        }
        return super.save(...arguments);
    },
});
