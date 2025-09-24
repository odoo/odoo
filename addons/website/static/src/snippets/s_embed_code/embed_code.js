import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { cloneContentEls } from "@website/js/utils";

export class EmbedCode extends Interaction {
    static selector = ".s_embed_code";

    setup() {
        this.embedCodeEl = this.el.querySelector(".s_embed_code_embedded");
    }

    destroy() {
        // Just before entering edit mode, reinitialize the snippet's content,
        // without <script> elements. This is both done so that scripts don't
        // affect the DOM in edit mode, and to remove elements that would have
        // been introduced by a script.
        const templateContent = this.el.querySelector("template.s_embed_code_saved").content;
        this.embedCodeEl.replaceChildren(cloneContentEls(templateContent));
    }
}

registry.category("public.interactions").add("website.embed_code", EmbedCode);
