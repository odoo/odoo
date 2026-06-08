import { ImageCropPlugin } from "@html_editor/main/media/image_crop_plugin";
import { ImageSavePlugin } from "@html_editor/main/media/image_save_plugin";
import { MediaPlugin } from "@html_editor/main/media/media_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

export class ProjectSharingMediaPlugin extends MediaPlugin {
    resources = {
        ...this.resources,
        toolbar_items: this.resources.toolbar_items.filter(
            item => item.id !== "replace_image"
        ),
    }
}

export class ProjectSharingImageSavePlugin extends ImageSavePlugin {
    async createAttachment({ el, imageData, resId }) {
        const response = JSON.parse(
            await this.services.http.post(
                "/project_sharing/attachment/add_image",
                {
                    name: el.dataset.fileName || "",
                    data: imageData,
                    res_id: resId,
                    access_token: "",
                    csrf_token: odoo.csrf_token,
                },
                "text"
            )
        );
        if (response.error) {
            this.services.notification.add(response.error, { type: "danger" });
            el.remove();
        }
        const attachment = response;
        attachment.image_src = "/web/image/" + attachment.id + "-" + attachment.name;
        return attachment;
    }
}

MAIN_PLUGINS.splice(MAIN_PLUGINS.indexOf(MediaPlugin), 1);
MAIN_PLUGINS.push(ProjectSharingMediaPlugin);
MAIN_PLUGINS.splice(MAIN_PLUGINS.indexOf(ImageSavePlugin), 1);
MAIN_PLUGINS.push(ProjectSharingImageSavePlugin);

MAIN_PLUGINS.splice(MAIN_PLUGINS.indexOf(ImageCropPlugin), 1);
