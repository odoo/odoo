import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export function sendRequest(route, params) {
    function _addInput(form, name, value) {
        const param = document.createElement("input");
        param.setAttribute("type", "hidden");
        param.setAttribute("name", name);
        param.setAttribute("value", value);
        form.appendChild(param);
    }

    const form = document.createElement("form");
    form.setAttribute("action", route);
    form.setAttribute("method", params.method || "POST");
    // This is an exception for the 404 page create page button, in backend we
    // want to open the response in the top window not in the iframe.
    if (params.forceTopWindow) {
        form.setAttribute("target", "_top");
    }

    if (odoo.csrf_token) {
        _addInput(form, "csrf_token", odoo.csrf_token);
    }

    for (const key in params) {
        const value = params[key];
        if (Array.isArray(value) && value.length) {
            for (const val of value) {
                _addInput(form, key, val);
            }
        } else {
            _addInput(form, key, value);
        }
    }

    document.body.appendChild(form);
    form.submit();
}
export class PostLink extends Interaction {
    static selector = ".post_link";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        // Distinguish _root according to node type.
        _select: () => this.el.matches("select") && this.el,
        _nonSelect: () => !this.el.matches("select") && this.el,
    };
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                o_post_link_js_loaded: true,
            }),
        },
        _nonSelect: {
            "t-on-click.prevent": this.onClickPost,
        },
        _select: {
            // In some browsers the click event is triggered when opening the select.
            "t-on-change.prevent": this.onClickPost,
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
