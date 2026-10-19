import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { SlideUploadDialog } from "@website_slides/js/public/components/slide_upload_dialog/slide_upload_dialog";

export class SlideUpload extends Interaction {
    static selector = ".o_wslides_js_slide_upload";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.openDialog,
        },
    };

    /**
     * Automatically opens the upload dialog if requested from query string.
     * If openModal is defined ( === '' ), opens the category selection dialog.
     * If openModal is a category name, opens the category's upload dialog.
     */
    start() {
        if ("openModal" in this.el.dataset) {
            this.openDialog();
            this.el.dataset.openModal = false;
        }
    }

    openDialog() {
        const data = this.el.dataset;
        this.services.dialog.add(SlideUploadDialog, {
            categoryId: parseInt(data.categoryId),
            channelId: parseInt(data.channelId),
            canPublish: data.canPublish === "True",
            canUpload: data.canUpload === "True",
            modulesToInstall: data.modulesToInstall ? JSON.parse(data.modulesToInstall) : [],
            openModal: data.openModal,
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.slide_upload", SlideUpload);
