//
// This file is meant to allow to switch the type of an input #password
// from password to text on mousedown on an input group.
// On mouse down, we see the password in clear text
// On mouse up, we hide it again.
//

import { registry } from "@web/core/registry";
import { Interaction } from "@website/core/interaction";

class ShowPassword extends Interaction {
    static selector = "#showPass";
    static dynamicContent = {
        "_root:t-on-pointerdown": "showText",
    };

    showText() {
        const passwordEl = this.el.closest(".input-group").querySelector("#password");
        passWordEl.setAttribute("type", "text");
        this.addDomListener(document.body, "pointerup", () => {
            passwordEl.setAttribute("type", "password");
        }, {once: true});
    }
}

registry
    .category("website.active_elements")
    .add("website.show_password", ShowPassword);
