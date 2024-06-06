/** @odoo-module **/

import publicWidget from "web.public.widget";
import { _t } from "@web/core/l10n/translation";
import { cloneContentEls } from "website.utils";

const EmbedCodeWidget = publicWidget.Widget.extend({
    selector: ".s_embed_code",
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        this.embedCodeEl = this.el.querySelector(".s_embed_code_embedded");

        // TODO this should not be the widget's job to create this element but
        // the job of the related editor option. This was done as a stable fix
        // and we should make an upgrade script in master to be able to get rid
        // of this code.
        if (!this.el.querySelector("template.s_embed_code_saved")) {
            const templateEl = document.createElement("template");
            templateEl.classList.add("s_embed_code_saved");
            templateEl.content.append(cloneContentEls(this.embedCodeEl, true));
            this.el.prepend(templateEl);
        }

        if (this.editableMode && this.embedCodeEl.offsetHeight === 0) {
            // Shows a placeholder message in edit mode to be able to select
            // the snippet if it's visually empty.
            const placeholderEl = document.createElement("div");
            placeholderEl.classList
                .add("s_embed_code_placeholder", "alert", "alert-info", "pt16", "pb16");
            placeholderEl.textContent = _t("Your Embed Code snippet doesn't have anything to display. Click on Edit to modify it.");
            this.el.querySelector(".s_embed_code_embedded").appendChild(placeholderEl);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);

        // Just before entering edit mode, reinitialize the snippet's content,
        // without <script> elements. This is both done so that scripts don't
        // affect the DOM in edit mode, and to remove elements that would have
        // been introduced by a script.
        if (!this.editableMode) {
            const templateContent = this.el.querySelector("template.s_embed_code_saved").content;
            this.embedCodeEl.replaceChildren(cloneContentEls(templateContent));
        }
    },
});

publicWidget.registry.EmbedCode = EmbedCodeWidget;

export default EmbedCodeWidget;
