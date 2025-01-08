import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from '@web/core/browser/browser';
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";

export class EmbedShare extends Interaction {
    static selector = ".oe_slide_js_embed_code_widget";
    dynamicContent = {
        ".o_embed_clipboard_button": { "t-on-click.prevent.withTarget": this.onClick },
    }

    async onClick(ev, currentTargetEl) {
        const tooltip = usePopover(Tooltip, { title: "Copied!", trigger: "manual", placement: "bottom" });
        const embedEl = document.querySelector("#wslides_share_embed_id_" + currentTargetEl.id.split("id_")[1]);
        await this.waitFor(browser.navigator.clipboard.writeText(embedEl.value || ""));
        tooltip.open(currentTargetEl)
        this.waitForTimeout(tooltip.close, 800);
    }
}

registry
    .category("public.interactions")
    .add("website_slides.embed_share", EmbedShare);
