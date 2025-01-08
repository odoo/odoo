import { EmbedCode } from "./embed_code";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";

const EmbedCodeEdit = I => class extends I {
    start() {
        if (this.embedCodeEl.offsetHeight === 0) {
            // Shows a placeholder message in edit mode to be able to select
            // the snippet if it's visually empty.
            const placeholderEl = document.createElement("div");
            placeholderEl.classList.add("s_embed_code_placeholder", "alert", "alert-info", "pt16", "pb16");
            placeholderEl.textContent = _t("Your Embed Code snippet doesn't have anything to display. Click on Edit to modify it.");
            this.embedCodeEl.appendChild(placeholderEl);
        }
    }
    destroy() { }
};

registry
    .category("public.interactions.edit")
    .add("website.embed_code", {
        Interaction: EmbedCode,
        mixin: EmbedCodeEdit,
    });
