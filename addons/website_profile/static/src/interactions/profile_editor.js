
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";

export class ProfileEditor extends Interaction {
    static selector = ".o_wprofile_editor_form";
    dynamicContent = {
        ".o_forum_profile_bio_edit": {
            "t-on-click.prevent": () => this.isEditingBio = true,
            "t-att-class": () => ({ "d-none": this.isEditingBio }),
        },
        ".o_forum_profile_bio_cancel_edit": {
            "t-on-click.prevent": () => this.isEditingBio = false,
            "t-att-class": () => ({ "d-none": !this.isEditingBio }),
        },
        ".o_forum_profile_bio_form": { "t-att-class": () => ({ "d-none": !this.isEditingBio }) },
        ".o_forum_profile_bio": { "t-att-class": () => ({ "d-none": this.isEditingBio, }) },
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
}

registry
    .category("public.interactions")
    .add("website_profile.profile_editor", ProfileEditor);
