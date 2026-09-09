/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { cloneContentEls } from "@website/js/utils";

const log = makeLogger("website.snippet.s_embed_code");

export class EmbedCode extends Interaction {
    static selector = ".s_embed_code";

    setup() {
        this.embedCodeEl = this.el.querySelector(".s_embed_code_embedded");
        log.lifecycle("setup", () => ({ hasEmbeddedEl: !!this.embedCodeEl }));
    }

    destroy() {
        log.lifecycle("destroy: restore saved template");
        const templateEl = this.el.querySelector("template.s_embed_code_saved");
        if (templateEl) {
            this.embedCodeEl.replaceChildren(cloneContentEls(templateEl.content));
        }
    }
}

registry.category("public.interactions").add("website.embed_code", EmbedCode);
