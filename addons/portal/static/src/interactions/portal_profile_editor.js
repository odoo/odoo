import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { checkFileSize } from "@web/core/utils/files";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class PortalProfileEditor extends Interaction {
    static selector = ".o_portal_profile_card";
    dynamicContent = {
        ".o_file_upload": {
            "t-on-change": this.onFileChange,
        },
        ".o_portal_profile_pic_edit": {
            "t-on-click.prevent": this.onEditProfile,
        },
        ".o_portal_profile_pic_clear": {
            "t-on-click.prevent": this.onClearProfile,
        },
    };

    setup() {
        this.notification = this.services.notification;
        this.fileInputEl = this.el.querySelector(".o_file_upload");
        this.profileImgEl = this.el.querySelector(".o_profile_picture_img");
        this.editBtnEl = this.el.querySelector(".o_portal_profile_pic_edit");
        this.clearBtnEl = this.el.querySelector(".o_portal_profile_pic_clear");
    }

    onEditProfile() {
        this.fileInputEl.click();
    }

    async onClearProfile() {
        await this.updateProfileImage({
            imageSrc: "/web/static/img/placeholder.png",
            imageData: false,
        });
    }

    async onFileChange() {
        const file = this.fileInputEl.files[0];
        if (!file || !checkFileSize(file.size, this.notification)) {
            return;
        }

        const dataUrl = await getDataURLFromFile(file);
        const base64Data = dataUrl.split(",")[1];
        await this.updateProfileImage({
            imageSrc: `data:${file.type};base64,${base64Data}`,
            imageData: base64Data,
        });
    }

    async updateProfileImage({ imageSrc, imageData }) {
        // save current image src to revert in case of error
        this._setButtonsDisabled(true);
        const prevProfileSrc = this.profileImgEl.src;
        try {
            await this._waitForImageLoad(imageSrc);
            await rpc("/my/profile/save", {
                user_id: parseInt(this.profileImgEl.dataset.userId),
                image_1920: imageData,
            });
        } catch {
            // revert to previous image
            this.profileImgEl.src = prevProfileSrc;
            this.notification.add(_t("An error occurred while saving your profile."), {
                type: "danger",
            });
        } finally {
            this._setButtonsDisabled(false);
            this.fileInputEl.value = '';
        }
    }

    _setButtonsDisabled(isDisabled) {
        this.editBtnEl.classList.toggle("disabled", isDisabled);
        this.clearBtnEl.classList.toggle("disabled", isDisabled);
    }

    _waitForImageLoad(imageSrc) {
        return new Promise((resolve, reject) => {
            this.profileImgEl.onload = resolve;
            this.profileImgEl.onerror = reject;
            this.profileImgEl.src = imageSrc;
        });
    }
}

registry.category("public.interactions").add("portal.portal_profile_editor", PortalProfileEditor);
