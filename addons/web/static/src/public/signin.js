import { addLoadingEffect } from "@web/core/utils/ui";
import { Interaction } from "./interaction";
import { registry } from "@web/core/registry";

class Signin extends Interaction {
    static selector = ".oe_login_form";
    dynamicContent = {
        _root: {
            "t-on-submit": this.onSubmit,
        },
    };

    /**
     * Prevents the user from crazy clicking:
     * Gives the button a loading effect if preventDefault was not already
     * called and modifies the preventDefault function of the event so that the
     * loading effect is removed if preventDefault() is called in a following
     * customization.
     *
     * @private
     * @param {Event} ev
     */
    onSubmit(ev) {
        if (!ev.defaultPrevented) {
            const btnEl = ev.currentTarget.querySelector('button[type="submit"]');
            const removeLoadingEffect = addLoadingEffect(btnEl);
            const oldPreventDefault = ev.preventDefault.bind(ev);
            ev.preventDefault = () => {
                removeLoadingEffect();
                oldPreventDefault();
            };
        }
    }
}

registry.category("public.interactions").add("public.signin", Signin);
