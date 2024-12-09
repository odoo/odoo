/** @odoo-module **/

import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { patch } from "@web/core/utils/patch";

patch(Wysiwyg.prototype, {
    async startEdition() {
        const res = await super.startEdition(...arguments);
        if (
            this.options.snippets &&
            this.odooEditor.document.querySelector("#ratingComposerRoot")
        ) {
            $(
                this.odooEditor.document
                    .querySelector("#ratingComposerRoot")
                    .shadowRoot.querySelector(".o-mail-RatingComposer")
            ).addClass("editor_enable");
        }
        return res;
    },
});
