import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

/**
 * Reimplement basic behavior of <button> on [role="button"], as they are often
 * overlooked.
 * Always use an actual button where you can.
 */
export class RoleButton extends Interaction {
    static selector = "[role='button']";
    dynamicContent = {
        _root: {
            "t-on-keydown": this.onKeydown,
            "t-att-tabindex": () => (this.isButtonDisabled() ? "-1" : "0"),
        },
    };

    isButtonDisabled() {
        return (
            (this.el.hasAttribute("aria-disabled") && this.el.ariaDisabled === "true") ||
            this.el.classList.contains("disabled")
        );
    }

    onKeydown(ev) {
        if (this.isButtonDisabled()) {
            return;
        }
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "space") {
            ev.preventDefault();
            this.el.click();
        }
    }
}

registry.category("public.interactions").add("portal.role_button", RoleButton);
registry.category("public.interactions.edit").add("portal.role_button", {
    Interaction: RoleButton,
});
