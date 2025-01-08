import { registry } from "@web/core/registry";
import { sendRequest } from "@website/js/utils";
import { Interaction } from "@web/public/interaction";

class PostLink extends Interaction {
    static selector = ".post_link";
    dynamicContent = {
        "_root": {
            "t-on-click": this.onClickPost,
            "t-att-class": () => ({"o_post_link_js_loaded": true})
        }
    };

    onClickPost(ev) {
        ev.preventDefault();
        const url = this.el.dataset.post || this.el.href;
        let data = {};
        for (const [key, value] of Object.entries(this.el.dataset)) {
            if (key.startsWith("post_")) {
                data[key.slice(5)] = value;
            }
        }
        sendRequest(url, data);
    }
}

registry.category("public.interactions").add("website.post_link", PostLink);
