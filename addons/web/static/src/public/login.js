import { Interaction } from "./interaction";
import { registry } from "@web/core/registry";

import { addLoadingEffect } from "@web/core/utils/ui";

export class Login extends Interaction {
    static selector = ".oe_login_form";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
    };

    /**
     * Prevents the user from crazy clicking:
     * Gives the button a loading effect if preventDefault was not already
     * called and modifies the preventDefault function of the event so that the
     * loading effect is removed if preventDefault() is called in a following
     * customization.
     *
     * @param {Event} ev
     */
    onSubmit(ev) {
        if (!ev.defaultPrevented) {
            const submitEl = ev.currentTarget.querySelector("button[type='submit']");
            const removeLoadingEffect = addLoadingEffect(submitEl);
            const oldPreventDefault = ev.preventDefault.bind(ev);
            ev.preventDefault = () => {
                removeLoadingEffect();
                oldPreventDefault();
            };
        }
    }
}

registry
    .category("public.interactions")
    .add("public.login", Login);
