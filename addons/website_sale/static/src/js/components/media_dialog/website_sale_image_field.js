import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { ImageField, imageField } from '@web/views/fields/image/image_field';
import { MultiMediaDialog } from './website_sale_media_dialog';
import { getVideoUrl } from './website_sale_one2many';

export class ProductMultiMediaImageField extends ImageField {
    static template = "website_sale.ImageField";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
    }

    /**
     * New method and a new edit button is introduced here to overwrite,
     * standard behavior of opening file input box in order to update a record.
     */

    onFileEdit(ev) {
        const isVideo = this.props.record.data.video_url;
        let mediaEl;
        if (isVideo) {
            mediaEl = document.createElement("img");
            mediaEl.dataset.src = this.props.record.data.video_url;
        }
        this.dialog.add(MultiMediaDialog, {
            onlyImages: true,
            media: mediaEl,
            activeTab: isVideo ? "VIDEOS" : "IMAGES",
            save: (el) => {}, // Simple rebound to fake its execution
            imageSave: this.onImageSave.bind(this),
            videoSave: this.onVideoSave.bind(this),
        });
    }

    async onImageSave(attachment) {
        const attachmentRecord = await this.orm.searchRead(
            "ir.attachment",
            [["id", "=", attachment[0].id]],
            ["id", "datas", "name"],
            {}
        );
        await this.props.record.update({
            [this.props.name]: attachmentRecord[0].datas,
            name: attachmentRecord[0].name,
        });
    }

    async onVideoSave(videoInfo) {
        const url = getVideoUrl(videoInfo[0].platform, videoInfo[0].videoId, videoInfo[0].params);
        await this.props.record.update({
            video_url: url.href,
            name: videoInfo[0].platform + " - [Video]",
        });
    }

    onFileRemove() {
        const parentRecord = this.props.record?._parentRecord.data;
        parentRecord?.product_template_image_ids
            ? parentRecord.product_template_image_ids.delete(this.props.record)
            : parentRecord.product_variant_image_ids.delete(this.props.record);
    }
}

export const productMultiMediaImageField = {
    ...imageField,
    component: ProductMultiMediaImageField,
};

registry.category("fields").add("multi_media_image", productMultiMediaImageField);
