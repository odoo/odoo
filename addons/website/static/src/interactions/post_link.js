import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { sendRequest } from "@website/js/utils";

export class PostLink extends Interaction {
    static selector = ".post_link";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.onClickPost,
            "t-att-class": () => ({
                o_post_link_js_loaded: true,
            }),
        },
    };

    onClickPost() {
        const data = {};
        for (const [key, value] of Object.entries(this.el.dataset)) {
            if (key.startsWith("post_")) {
                data[key.slice(5)] = value;
            }
        }
        sendRequest(this.el.dataset.post || this.el.href || this.el.value, data);
    }
}

registry.category("public.interactions").add("website.post_link", PostLink);
