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
        this.profileEl = this.el.querySelector(".o_profile_picture");
        this.editBtnEl = this.el.querySelector(".o_portal_profile_pic_edit");
        this.clearBtnEl = this.el.querySelector(".o_portal_profile_pic_clear");
    }

    onEditProfile() {
        this.fileInputEl.click();
    }

    async onClearProfile() {
        await this.updateProfileImage({
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
            imageData: base64Data,
        });
    }

    async updateProfileImage({ imageData }) {
        this.setButtonsDisabled(true);
        try {
            await rpc("/my/profile/save", {
                user_id: parseInt(this.profileEl.dataset.userId),
                image_1920: imageData,
            });
        } catch {
            this.notification.add(_t("An error occurred while saving your profile."), {
                type: "danger",
            });
        } finally {
            this.setButtonsDisabled(false);
            this.fileInputEl.value = '';
            // Reload the image by adding a timestamp to bypass browser cache.
            // This is necessary because the image URL remains the same,
            // and browsers may cache it, preventing the updated image
            // from being displayed.
            const imgEl = this.profileEl.querySelector('img');
            const  imageSrc = imgEl.getAttribute('src').split('?')[0];
            imgEl.setAttribute('src', `${imageSrc}?t=${Date.now()}`);
        }
    }

    setButtonsDisabled(isDisabled) {
        this.editBtnEl.classList.toggle("disabled", isDisabled);
        this.clearBtnEl.classList.toggle("disabled", isDisabled);
    }
}

registry.category("public.interactions").add("portal.portal_profile_editor", PortalProfileEditor);
