import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';
import { MultiMediaDialog } from './website_sale_media_dialog';

/*
 * This method is copied from enterprise/knowledge/static/src/js/knowledge_utils.js
 * We can't import it directly because it adds a dependency on enterprise.
 */
export function getVideoUrl(platform, videoId, params) {
    let url;
    switch (platform) {
        case "youtube":
            url = new URL(`https://www.youtube.com/embed/${videoId}`);
            break;
        case "vimeo":
            url = new URL(`https://player.vimeo.com/video/${videoId}`);
            break;
        case "dailymotion":
            url = new URL(`https://www.dailymotion.com/embed/video/${videoId}`);
            break;
        case "instagram":
            url = new URL(`https://www.instagram.com/p/${videoId}/embed`);
            break;
        case "youku":
            url = new URL(`https://player.youku.com/embed/${videoId}`);
            break;
        default:
            throw new Error();
    }
    url.search = new URLSearchParams(params);
    return url;
}

export class ProductMediaViewer extends X2ManyField {
    static template = "website_sale.ProductMediaViewer";

    setup() {
        super.setup();
        this.dialogs = useService("dialog");
        this.orm = useService("orm");
        this.supportedFields = ["image_1920", "image_1024", "image_512", "image_256", "image_128"];
    }

    addMedia() {
        this.dialogs.add(MultiMediaDialog, {
            save: (el) => {}, // Simple rebound to fake its execution
            multiImages: true,
            imageSave: this.onImageSave.bind(this),
            videoSave: this.onVideoSave.bind(this),
        });
    }

    onVideoSave(videoInfo) {
        const url = getVideoUrl(videoInfo[0].platform, videoInfo[0].videoId, videoInfo[0].params);
        const videoList = this.props.record.data[this.props.name];
        videoList.addNewRecord({ position: "bottom" }).then((record) => {
            record.update({ name: videoInfo[0].platform + " - [Video]", video_url: url.href });
        });
    }

    async onImageSave(attachments) {
        const attachmentIds = attachments.map((attachment) => attachment.id);
        const attachmentRecords = await this.orm.searchRead(
            "ir.attachment",
            [["id", "in", attachmentIds]],
            ["id", "datas", "name"],
            {}
        );
        attachmentRecords.forEach((attachment) => {
            const imageList = this.props.record.data[this.props.name];
            imageList.addNewRecord({ position: "bottom" }).then((record) => {
                const activeFields = imageList.activeFields;
                const updateData = {};
                for (const field in activeFields) {
                    if (attachment.datas && this.supportedFields.includes(field)) {
                        updateData[field] = attachment.datas;
                        updateData["name"] = attachment.name;
                    }
                }
                record.update(updateData);
            });
        });
    }

    async onAdd({ context, editable } = {}) {
        this.addMedia();
    }
}

export const productMediaViewer = {
    ...x2ManyField,
    component: ProductMediaViewer,
};

registry.category("fields").add("product_media_viewer", productMediaViewer);
