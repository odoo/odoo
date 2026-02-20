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
        this._toggleButtons(true);
        try {
            await rpc("/my/profile/save", {
                user_id: parseInt(this.profileEl.dataset.oeId),
                image_1920: imageData,
            });
        } catch {
            this.notification.add(_t("An error occurred while saving your profile."), {
                type: "danger",
            });
        } finally {
            this._toggleButtons(false);
            this.fileInputEl.value = '';
            // force reload of the image to reflect changes or revert to
            // previous image in case of error
            const imgEl = this.profileEl.querySelector('img');
            const newImg = imgEl.cloneNode(true);
            imgEl.replaceWith(newImg);
        }
    }

    _toggleButtons(isDisabled) {
        this.editBtnEl.classList.toggle("disabled", isDisabled);
        this.clearBtnEl.classList.toggle("disabled", isDisabled);
    }
}

registry.category("public.interactions").add("portal.portal_profile_editor", PortalProfileEditor);
