import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PortalPasskeyPopover extends Interaction {
    static selector = ".o_passkey_dropdown_btn";
    dynamicContent = {
        _root: { "t-on-click": this.onClick }
    }

    setup() {
        this.dropDown = this.el.parentElement.querySelector(".o_passkey_dropdown")
    }

    async onClick() {
        this.dropDown.classList.toggle("d-none");
    }
}

registry
    .category("public.interactions")
    .add("auth_passkey_portal.popover", PortalPasskeyPopover);

