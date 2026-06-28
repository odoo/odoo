import { registry } from "@web/core/registry";
import { resizeTextArea } from "@web/core/utils/autoresize";
import { addLoadingEffect } from "@web/core/utils/ui";
import { Interaction } from "@web/public/interaction";

export class LinkedinMessageEditorInteraction extends Interaction {
    static selector = "form.o_card_campaign_linkedin_share_composer_form";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmitForm.bind(this) },
        "textarea[name='text']": { "t-on-input": this.onTextInput.bind(this) },
    };

    onSubmitForm(ev) {
        addLoadingEffect(ev.target.querySelector("button[type='submit']"));
    }

    onTextInput(ev) {
        // should match the original default height
        resizeTextArea(ev.target, { minimumHeight: 128 });
    }
}

registry
    .category("public.interactions")
    .add("marketing_card.linkedin_message_editor", LinkedinMessageEditorInteraction);
