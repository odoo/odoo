import { Component, onWillDestroy, useAttachedEl } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { sendRequest } from "@website/js/utils";

class PostLink extends Component {
    static selector = ".post_link";
    static dynamicContent = {
        "root:t-on-click": "onClickPost"
    }
    
    setup() {
        this.el = useAttachedEl();
        // Allows the link to be interacted with only when Javascript is loaded.
        this.el.classList.add("o_post_link_js_loaded");
        onWillDestroy(() => {
            this.el.classList.remove("o_post_link_js_loaded");
        });
    }

    onClickPost(ev) {
        ev.preventDefault();
        const url = this.el.dataset.post || this.el.href;
        let data = {};
        for (let [key, value] of Object.entries(this.el.dataset)) {
            if (key.startsWith('post_')) {
                data[key.slice(5)] = value;
            }
        }
        sendRequest(url, data);
    }
}

registry.category("website.active_elements").add("website.post_link", PostLink);
