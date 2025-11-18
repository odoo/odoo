import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { getTemplate } from "@web/core/templates";
import { KeepLast } from "@web/core/utils/concurrency";
import { SIZES, MEDIAS_BREAKPOINTS } from "@web/core/ui/ui_service";

export class SearchBar extends Interaction {
    static selector = ".o_searchbar_form";
    dynamicContent = {
        _root: {
            "t-on-focusout": this.debounced(this.onFocusOut, 100),
            "t-on-safarihack": (ev) => (this.linkHasFocus = ev.detail.linkHasFocus),
            "t-att-class": () => ({
                dropdown: this.hasDropdown,
                show: this.hasDropdown,
            }),
        },
        ".search-query": {
            "t-on-input": this.debounced(this.onInput, 400),
            "t-on-keydown": this.onKeydown,
            "t-on-search": this.onSearch,
        },
    };
    autocompleteMinWidth = 300;

    setup() {
        this.keepLast = new KeepLast();
        this.inputEl = this.el.querySelector(".search-query");
        this.menuEl = null;
        this.searchType = this.inputEl.dataset.searchType;
        const orderByEl = this.el.querySelector(".o_search_order_by");
        const form = orderByEl.closest("form");
        this.order = orderByEl.value;
        this.limit = parseInt(this.inputEl.dataset.limit) || 6;
        this.wasEmpty = !this.inputEl.value;
        this.linkHasFocus = false;
        if (this.limit) {
            this.inputEl.setAttribute("autocomplete", "off");
        }
        const dataset = this.inputEl.dataset;
        this.options = {
            searchType: dataset.searchType,
            // Make it easy for customization to disable fuzzy matching on specific searchboxes
            allowFuzzy: !(dataset.noFuzzy && JSON.parse(dataset.noFuzzy)),
        };
        for (const fieldEl of form.querySelectorAll("input[type='hidden']")) {
            this.options[fieldEl.name] = fieldEl.value;
        }
        const action =
            form.getAttribute("action") || window.location.pathname + window.location.search;
        const [urlPath, urlParams] = action.split("?");
        if (urlParams) {
            for (const keyValue of urlParams.split("&")) {
                const [key, value] = keyValue.split("=");
                if (value && key !== "search") {
                    // Decode URI parameters: revert + to space then decodeURIComponent.
                    this.options[decodeURIComponent(key.replace(/\+/g, "%20"))] =
                        decodeURIComponent(value.replace(/\+/g, "%20"));
                }
            }
        }
        const pathParts = urlPath.split("/");
        for (const index in pathParts) {
            const value = decodeURIComponent(pathParts[index]);
            const indexNumber = parseInt(index);
            if (indexNumber > 0 && /-[0-9]+$/.test(value)) {
                // is sluggish
                this.options[decodeURIComponent(pathParts[indexNumber - 1])] = value;
            }
        }
    }

    start() {
        if (this.inputEl.dataset.noFuzzy && JSON.parse(this.inputEl.dataset.noFuzzy)) {
            const noFuzzyEl = document.createElement("input");
            noFuzzyEl.setAttribute("type", "hidden");
            noFuzzyEl.setAttribute("name", "noFuzzy");
            noFuzzyEl.setAttribute("value", "true");
            this.insert(noFuzzyEl, this.inputEl);
        }
    }

    destroy() {
        this.render(null);
    }

    getDisplayType() {
        if (this.el.clientWidth > MEDIAS_BREAKPOINTS[SIZES.SM].maxWidth) {
            return "columns";
        }
        return "list";
    }

    async fetch() {
        const res = await rpc("/website/snippet/autocomplete", {
            search_type: this.searchType,
            term: this.inputEl.value,
            order: this.order,
            limit: this.limit,
            max_nb_chars: Math.round(
                Math.max(
                    this.autocompleteMinWidth,
                    parseInt(this.el.clientWidth / (this.getDisplayType() === "columns" ? 3 : 1))
                ) * 0.22
            ),
            options: this.options,
        });

        const field_set = new Set(this.getFieldsNames());
        for (const group in res.results) {
            const data = res.results[group].data;
            data.forEach((record) => {
                for (const key in record) {
                    if (field_set.has(key) && record[key]) {
                        record[key] = markup(record[key]);
                    }
                }
            });
        }
        return res;
    }

    /**
     * @param {Object} res
     */
    render(res) {
        if (this.menuEl) {
            this.services["public.interactions"].stopInteractions(this.menuEl);
        }
        const prevMenuEl = this.menuEl;
        if (res && this.limit) {
            const results = res.results;
            let template = "website.s_searchbar.autocomplete";
            const candidate = template + "." + this.searchType;
            if (getTemplate(candidate)) {
                template = candidate;
            }
            this.menuEl = this.renderAt(
                template,
                {
                    results: results,
                    parts: res["parts"],
                    limit: this.limit,
                    search: this.inputEl.value,
                    fuzzySearch: res["fuzzy_search"],
                    widget: this.options,
                    displayType: this.getDisplayType(),
                },
                this.el
            )[0];
        }
        this.hasDropdown = !!res;
        prevMenuEl?.remove();
    }

    getFieldsNames() {
        return [
            "description",
            "detail",
            "detail_extra",
            "detail_strike",
            "extra_link",
            "name",
            "tags",
        ];
    }

    async onInput() {
        if (!this.limit) {
            return;
        }
        if (this.searchType === "all" && !this.inputEl.value.trim().length) {
            this.render();
        } else {
            const res = await this.keepLast.add(this.waitFor(this.fetch()));
            this.render(res);
        }
    }

    onFocusOut() {
        if (
            !this.linkHasFocus &&
            document.activeElement?.closest(".o_searchbar_form") !== this.el
        ) {
            this.render();
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onKeydown(ev) {
        switch (ev.key) {
            case "Escape":
                this.render();
                break;
            case "ArrowUp":
            case "ArrowDown":
                ev.preventDefault();
                if (this.menuEl) {
                    const focusableEls = [this.inputEl, ...this.menuEl.children];
                    const focusedEl = document.activeElement;
                    const currentIndex = focusableEls.indexOf(focusedEl) || 0;
                    const delta = ev.key === "ArrowUp" ? focusableEls.length - 1 : 1;
                    const nextIndex = (currentIndex + delta) % focusableEls.length;
                    const nextFocusedEl = focusableEls[nextIndex];
                    nextFocusedEl.focus();
                }
                break;
            case "Enter":
                this.limit = 0; // prevent autocomplete
                break;
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onSearch(ev) {
        if (this.inputEl.value) {
            // actual search
            this.limit = 0; // prevent autocomplete
        } else {
            // clear button clicked
            this.render(); // remove existing suggestions
            ev.preventDefault();
        }
    }
}

registry.category("public.interactions").add("website.search_bar", SearchBar);
