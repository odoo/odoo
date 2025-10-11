import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";
import { checkFileSize } from "@web/core/utils/files";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

export class PortalProfileEditor extends Interaction {
    static selector = ".o_portal_profile_editor";

    dynamicContent = {
        ".o_file_upload": { "t-on-change": this.onFileChange },
        ".o_portal_profile_pic_edit": { "t-on-click.prevent": this.onEditProfilePicClick },
        ".o_portal_profile_pic_clear": { "t-on-click.prevent": this.onClearProfileImg },
        ".o_portal_profile_pic_save": { "t-on-click.prevent": this.onSave },
    };

    setup() {
        this.notification = this.services.notification;

        this.fileInputEl = this.el.querySelector(".o_file_upload");
        this.profileImgEl = this.el.querySelector(".o_profile_picture_img");
        this.saveButtonEl = this.el.querySelector(".o_portal_profile_pic_save");

        this.userId = this.profileImgEl.dataset.userId;
        this.profileImgData = null;
    }

    // --- Event Handlers ---

    onEditProfilePicClick() {
        this.fileInputEl.click();
    }

    onClearProfileImg() {
        this.profileImgData = false;
        this.profileImgEl.src = "/web/static/img/placeholder.png";
        this.saveButtonEl.classList.remove("d-none");
    }

    async onFileChange() {
        for (const file of this.fileInputEl.files) {
            // Validate file size
            if (!checkFileSize(file.size, this.notification)) {
                return;
            }

            const dataUrl = await getDataURLFromFile(file);

            if (!file.size) {
                console.warn(`Error uploading file: ${file.name}`);
                this.notification.add(_t("There was a problem while uploading your file."), {
                    type: "danger",
                });
                return;
            }

            this.onUploadProfileImg({
                name: file.name,
                size: file.size,
                type: file.type,
                data: dataUrl.split(",")[1],
            });
        }
    }

    onUploadProfileImg(file) {
        this.profileImgEl.src = `data:${file.type};base64,${file.data}`;
        this.profileImgData = file.data;
        this.saveButtonEl.classList.remove("d-none");
    }

    async onSave() {
        const payload = { user_id: this.userId };

        if (this.profileImgData !== null) {
            payload.image_1920 = this.profileImgData;
        }

        try {
            await rpc("/my/profile/user/save", payload);
            this.notification.add(_t("Your profile has been updated."), { type: "success" });
            browser.location.reload();
        } catch {
            this.notification.add(_t("An error occurred while saving your profile."), {
                type: "danger",
            });
        }
    }
}

registry.category("public.interactions").add("portal.portal_profile_editor", PortalProfileEditor);
