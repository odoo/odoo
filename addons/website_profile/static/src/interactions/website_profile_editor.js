
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";

export class WebsiteProfileEditor extends Interaction {
    static selector = ".o_wprofile_editor_form";
    dynamicContent = {
        ".o_forum_file_upload": { "t-on-change": this.onUploadFile },
        ".o_forum_profile_pic_edit": { "t-on-click.prevent": this.onClickEditProfilePic },
        ".o_forum_profile_pic_clear": { "t-on-click": this.onClickClearProfilePic },
        ".o_forum_profile_bio_edit": {
            "t-on-click.prevent": () => this.isEditingBio = true,
            "t-att-class": () => ({ "d-none": this.editingBio }),
        },
        ".o_forum_profile_bio_cancel_edit": {
            "t-on-click.prevent": () => this.isEditingBio = false,
            "t-att-class": () => ({ "d-none": !this.editingBio }),
        },
        ".o_forum_profile_bio_form": { "t-att-class": () => ({ "d-none": !this.editingBio }) },
        ".o_forum_profile_bio": { "t-att-class": () => ({ "d-none": this.editingBio, }) },
    };

    setup() {
        this.isEditingBio = false;

        this.textareaEl = this.el.querySelector("textarea.o_wysiwyg_loader");

        this.options = {
            recordInfo: {
                context: this.services.website_page.context,
                res_model: "res.users",
                res_id: parseInt(this.el.querySelector("input[name=user_id]").value),
            },
            value: this.textareaEl.getAttribute("content"),
            resizable: true,
            userGeneratedContent: true,
        };

        if (this.textareaEl.attributes.placeholder) {
            this.options.placeholder = this.textareaEl.attributes.placeholder.value;
        }
    }

    async willStart() {
        await loadWysiwygFromTextarea(this, this.textareaEl, this.options);
    }

    onClickEditProfilePic(ev) {
        ev.currentTarget.closest("form").querySelector(".o_forum_file_upload").click();
    }

    onClickClearProfilePic(ev) {
        const formEl = ev.currentTarget.closest("form");
        formEl.querySelector(".o_wforum_avatar_img").src = "/web/static/img/placeholder.png";
        const inputElement = document.createElement("input");
        inputElement.setAttribute("name", "clear_image");
        inputElement.setAttribute("id", "forum_clear_image");
        inputElement.setAttribute("type", "hidden");
        this.insert(inputElement, formEl);
    }

    onUploadFile(ev) {
        if (!ev.currentTarget.files.length) {
            return;
        }
        const formEl = ev.currentTarget.closest("form");
        const reader = new window.FileReader();
        reader.readAsDataURL(ev.currentTarget.files[0]);
        this.addListener(reader, "load", (ev) => formEl.querySelector(".o_wforum_avatar_img").src = ev.target.result);
        formEl.querySelector("#forum_clear_image")?.remove();
    }

}

registry
    .category("public.interactions")
    .add("website_profile.website_profile_editor", WebsiteProfileEditor);
