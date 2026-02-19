import { patch } from "@web/core/utils/patch";
import { LinkPlugin } from "@html_editor/main/link/link_plugin";

patch(LinkPlugin.prototype, {
    setup() {
        super.setup();
    },
    applyLinkCallback(...args) {
        if (this.linkInDocument) {
            if (args[0].relValue) {
                this.linkInDocument.setAttribute("rel", args[0].relValue);
            } else {
                this.linkInDocument.removeAttribute("rel");
            }
            if (args[0].linkTarget) {
                this.linkInDocument.setAttribute("target", args[0].linkTarget);
            } else {
                this.linkInDocument.removeAttribute("target");
            }
        }
        const result = super.applyLinkCallback(...args);
        return result;
    },
});
