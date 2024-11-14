import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class ProfilePicture extends Interaction {
    static selector = ".o_portal_picture_card";
    dynamicContent = {
        ".o_file_upload": { "t-on-change": this.onFileChange },
        ".o_portal_profile_pic_edit" : { "t-on-click.prevent": this.onEditProfilePicClick },
        ".o_portal_profile_pic_clear": { "t-on-click.prevent": this.onClearProfilePicClick },
    }

    setup() {
        this.notification = this.services.notification;
        this.fileUploadEl = this.el.querySelector(".o_file_upload");
        this.pictureCardEl = this.el.querySelector(".o_wportal_avatar_img");
        this.currentProfileSrc = this.pictureCardEl.src;
    }

    onEditProfilePicClick() {
        this.fileUploadEl.click();
    }

    onClearProfilePicClick() {
        const pictureCardEl = this.el;

        const removeProfileInput = pictureCardEl.querySelector("input#remove_profile");
        const clearImageInput = pictureCardEl.querySelector("input#forum_clear_image");
        if (!removeProfileInput && !clearImageInput) {
            this.pictureCardEl.src =
                "/web/static/img/placeholder.png";

            const inputElement = document.createElement("input");
            inputElement.type = "hidden";
            Object.assign(
                inputElement,
                this.el.parentElement.querySelector("span")?.textContent === "Public Profile"
                    ? { name: "clear_image", id: "forum_clear_image" }
                    : { name: "remove_profile", id: "remove_profile", value: "true" }
            );
            pictureCardEl.appendChild(inputElement);
        }
    }

    onFileChange() {
        if (!this.fileUploadEl.files.length) {
            return;
        }
        const pictureCardEl = this.el;
        const reader = new FileReader();
        const file = this.fileUploadEl.files[0];
        reader.onload = (ev) => {
            const img = new Image();
            img.onload = () => {
                this.pictureCardEl.src = ev.target.result;
                pictureCardEl.querySelector("input#remove_profile")?.remove();
            };
            img.onerror = () => {
                this.notification.add(_t("The selected image is broken or invalid."), {
                    type: "danger",
                });
                this.fileUploadEl.value = null;
                this.pictureCardEl.src = this.currentProfileSrc;
            };

            img.src = ev.target.result;
        };
        reader.onerror = () => {
            this.notification.add(_t("Failed to read the selected image."), {
                type: "danger",
            });
        };

        reader.readAsDataURL(file);
    }
}

registry
    .category("public.interactions")
    .add("portal.portal_picture", ProfilePicture);
