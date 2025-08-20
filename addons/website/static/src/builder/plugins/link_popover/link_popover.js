import { LinkPopover } from "@html_editor/main/link/link_popover";
import { patch } from "@web/core/utils/patch";

patch(LinkPopover, {
    template: "website.linkPopover",
});

patch(LinkPopover.prototype, {
    get classes() {
        let classes = super.classes;
        if (this.state.type === "primary" || this.state.type === "secondary") {
            if (this.state.buttonSize) {
                classes += ` btn-${this.state.buttonSize}`;
            }
        }
        return classes.trim();
    }
});
