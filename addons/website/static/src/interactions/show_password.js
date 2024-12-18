//
// This file is meant to allow to switch the type of an input #password
// from password to text on mousedown on an input group.
// On mouse down, we see the password in clear text
// On mouse up, we hide it again.
//

import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

class ShowPassword extends Interaction {
    static selector = "#showPass";
    dynamicContent = {
        "_root": { "t-on-pointerdown": this.showText },
    };

    showText() {
        const passwordEl = this.el
            .closest(".input-group")
            .querySelector("#password");
        passwordEl.setAttribute("type", "text");
        this.addListener(
            document.body,
            "pointerup",
            () => {
                passwordEl.setAttribute("type", "password");
            },
            { once: true },
        );
    }
}

registry
    .category("public.interactions")
    .add("website.show_password", ShowPassword);
