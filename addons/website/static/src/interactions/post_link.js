import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";

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

function _appendParam(params, name, value) {
    if (!name || value === undefined || value === null || value === "") {
        return;
    }
    params.append(name, value);
}

function _getParamEntries(value) {
    if (!value || !String(value).includes("=")) {
        return [];
    }
    return [...new URLSearchParams(value).entries()];
}

function _collectMobileFilterParams(container) {
    const params = new URLSearchParams();
    const filterNames = new Set();
    const tagValues = [];
    const elements = Array.from(container.querySelectorAll("input, select, textarea"));
    for (const element of elements) {
        if (!element.name || element.disabled) {
            continue;
        }
        filterNames.add(element.name);
        const type = element.type;
        if ((type === "checkbox" || type === "radio") && !element.checked) {
            continue;
        }
        if (type === "radio") {
            const entries = _getParamEntries(element.value);
            if (entries.length) {
                for (const [name, value] of entries) {
                    filterNames.add(name);
                    _appendParam(params, name, value);
                }
                continue;
            }
        }
        if (element.name === "tags") {
            tagValues.push(element.dataset.slug || element.value);
            continue;
        }
        _appendParam(params, element.name, element.value);
    }
    if (tagValues.length) {
        params.set("tags", [...new Set(tagValues)].join(","));
    }
    return { params, filterNames };
}

function _applyParams(searchParams, params) {
    for (const [name, value] of params.entries()) {
        searchParams.append(name, value);
    }
}

function _buildFilterUrl(offcanvasEl, params, filterNames) {
    const currentUrl = new URL(window.location.href);
    const url = new URL(offcanvasEl.dataset.filterUrl, window.location.origin);
    const searchParams = new URLSearchParams(currentUrl.search);
    for (const name of ["page", "tags", ...filterNames]) {
        searchParams.delete(name);
    }
    _applyParams(searchParams, params);
    url.search = searchParams.toString();
    return `${url.pathname}${url.search}`;
}

export class MobileFilterButtons extends Interaction {
    static selector = ".offcanvas-footer";

    dynamicContent = {
        ".o_mobile_filter_apply": {
            "t-on-click.prevent": this.onApplyFilters,
        },
        ".o_mobile_filter_clear": {
            "t-on-click.prevent": this.onClearFilters,
        },
    };

    onApplyFilters() {
        const offcanvasEl = this.el.closest(".o_website_offcanvas, .offcanvas");
        const { params, filterNames } = _collectMobileFilterParams(offcanvasEl);
        redirect(_buildFilterUrl(offcanvasEl, params, filterNames));
    }

    onClearFilters() {
        const offcanvasEl = this.el.closest(".o_website_offcanvas, .offcanvas");
        redirect(offcanvasEl.dataset.filterUrl);
    }
}

registry.category("public.interactions").add("website.post_link", PostLink);
registry.category("public.interactions").add("website.mobile_filter_buttons", MobileFilterButtons);
