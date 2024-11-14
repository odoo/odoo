import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class ProfilePicture extends Interaction {
    static selector = ".o_portal_picture_card";
    dynamicContent = {
        ".o_file_upload": { "t-on-change": this.onFileChange },
        ".o_portal_profile_pic_edit": { "t-on-click.prevent": this.onEditProfilePicClick },
        ".o_portal_profile_pic_clear": { "t-on-click.prevent": this.onClearProfilePicClick },
    };

    setup() {
        this.notification = this.services.notification;
        this.fileUploadEl = this.el.querySelector(".o_file_upload");
        this.avatarImgEl = this.el.querySelector(".o_wportal_avatar_img");
        this.lastValidImage = this.avatarImgEl.src;
    }

    onEditProfilePicClick() {
        this.fileUploadEl.click();
    }

    onClearProfilePicClick() {
        if (!this.el.querySelector("input[name=remove_profile]")) {
            this.avatarImgEl.src = "/web/image/web.image_placeholder";
            this.fileUploadEl.value = "";
            const inputEl = document.createElement("input");
            Object.assign(inputEl, { type: "hidden", name: "remove_profile" });
            this.el.appendChild(inputEl);
        }
    }

    async onFileChange() {
        const file = this.fileUploadEl.files[0];
        if (!file) return;
        try {
            const imgURL = await this.readImageURL(file);
            await this.loadImage(imgURL);
            this.avatarImgEl.src = imgURL;
            this.lastValidFile = file;
            this.el.querySelector("input[name=remove_profile]")?.remove();
        } catch (error) {
            this.notification.add(error, { type: "danger" });
            await this.restoreLastValidProfileImg();
        }
    }

    async restoreLastValidProfileImg() {
        if (this.lastValidImage instanceof File) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(this.lastValidFile);
            this.fileUploadEl.files = dataTransfer.files;
            this.avatarImgEl.src = await this.readImageURL(this.lastValidFile);
        } else {
            this.fileUploadEl.value = "";
            this.avatarImgEl.src = this.lastValidFile;
        }
    }

    readImageURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = ({ target: { result } }) => resolve(result);
            reader.onerror = () => reject(_t("Failed to read the selected image."));
            reader.readAsDataURL(file);
        });
    }

    loadImage(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(src);
            img.onerror = () => reject(_t("The selected image is broken or invalid."));
            img.src = src;
        });
    }
}

registry.category("public.interactions").add("portal.portal_picture", ProfilePicture);
