import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { _t } from "@web/core/l10n/translation";
import { cloneContentEls } from "@website/js/utils";

export class EmbedCode extends Interaction {
    static selector = ".s_embed_code";
    // TODO Support edit mode.
    disabledInEditableMode = false;

    setup() {
        this.embedCodeEl = this.el.querySelector(".s_embed_code_embedded");
    }

    start() {
        // TODO Support edit mode.
        if (this.editableMode && this.embedCodeEl.offsetHeight === 0) {
            // Shows a placeholder message in edit mode to be able to select
            // the snippet if it's visually empty.
            const placeholderEl = document.createElement("div");
            placeholderEl.classList
                .add("s_embed_code_placeholder", "alert", "alert-info", "pt16", "pb16");
            placeholderEl.textContent = _t("Your Embed Code snippet doesn't have anything to display. Click on Edit to modify it.");
            this.embedCodeEl.appendChild(placeholderEl);
        }
    }

    destroy() {
        // Just before entering edit mode, reinitialize the snippet's content,
        // without <script> elements. This is both done so that scripts don't
        // affect the DOM in edit mode, and to remove elements that would have
        // been introduced by a script.
        // TODO Support edit mode.
        // if (!this.editableMode) {
            const templateContent = this.el.querySelector("template.s_embed_code_saved").content;
            this.embedCodeEl.replaceChildren(cloneContentEls(templateContent));
        // }
    }
}

registry.category("public.interactions").add("website.embed_code", EmbedCode);
