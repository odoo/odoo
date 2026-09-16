/** @odoo-module native */
import { markup } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";
import { KeepLast } from "@web/core/utils/concurrency";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.snippet.s_searchbar");

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
        // `|| 5` turned the editor's own "0 results" into 5. The Suggestions
        // option is a BuilderNumberInput with min="0", and the option panel
        // hides the display sub-options when it is 0, so 0 is a supported
        // setting meaning "no autocomplete dropdown" -- which the three
        // `this.limit` guards below exist to honour and never saw.
        const configuredLimit = parseInt(this.inputEl.dataset.limit);
        this.limit = Number.isNaN(configuredLimit) ? 5 : configuredLimit;
        this.wasEmpty = !this.inputEl.value;
        this.linkHasFocus = false;
        if (this.limit) {
            this.inputEl.setAttribute("autocomplete", "off");
        }
        const dataset = this.inputEl.dataset;
        this.options = {
            displayImage: dataset.displayImage && JSON.parse(dataset.displayImage),
            displayDescription:
                dataset.displayDescription && JSON.parse(dataset.displayDescription),
            displayExtraLink:
                dataset.displayExtraLink && JSON.parse(dataset.displayExtraLink),
            displayDetail: dataset.displayDetail && JSON.parse(dataset.displayDetail),
            allowFuzzy: !(dataset.noFuzzy && JSON.parse(dataset.noFuzzy)),
        };
        for (const fieldEl of form.querySelectorAll("input[type='hidden']")) {
            this.options[fieldEl.name] = fieldEl.value;
        }
        const action =
            form.getAttribute("action") ||
            window.location.pathname + window.location.search;
        const [urlPath, urlParams] = action.split("?");
        if (urlParams) {
            for (const keyValue of urlParams.split("&")) {
                const [key, value] = keyValue.split("=");
                if (value && key !== "search") {
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
                this.options[decodeURIComponent(pathParts[indexNumber - 1])] = value;
            }
        }
        log.lifecycle("setup", () => ({
            searchType: this.searchType,
            limit: this.limit,
            order: this.order,
            options: Object.keys(this.options),
        }));
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
        log.lifecycle("destroy: closing dropdown");
        this.render(null);
    }

    async fetch() {
        const endFetch = log.perf("fetch autocomplete", () => ({
            searchType: this.searchType,
        }));
        const res = await rpc("/website/snippet/autocomplete", {
            search_type: this.searchType,
            term: this.inputEl.value,
            order: this.order,
            limit: this.limit,
            max_nb_chars: Math.round(
                Math.max(this.autocompleteMinWidth, parseInt(this.el.clientWidth)) *
                    0.22,
            ),
            options: this.options,
        });
        endFetch(() => ({
            results: res.results.length,
            resultsCount: res.results_count,
            fuzzy: !!res.fuzzy_search,
        }));
        const fieldNames = this.getFieldsNames();
        res.results.forEach((record) => {
            for (const fieldName of fieldNames) {
                if (record[fieldName]) {
                    record[fieldName] = markup(record[fieldName]);
                }
            }
        });
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
            const results = res["results"];
            let template = "website.s_searchbar.autocomplete";
            const candidate = template + "." + this.searchType;
            if (getTemplate(candidate)) {
                template = candidate;
            }
            log.pipeline("render: rendering results", () => ({
                template,
                results: results.length,
                resultsCount: res["results_count"],
            }));
            this.menuEl = this.renderAt(
                template,
                {
                    results: results,
                    parts: res["parts"],
                    hasMoreResults: results.length < res["results_count"],
                    search: this.inputEl.value,
                    fuzzySearch: res["fuzzy_search"],
                    widget: this.options,
                },
                this.el,
            )[0];
        }
        log.logic("render: dropdown state", () => ({
            open: !!res,
            limit: this.limit,
            hadMenu: !!prevMenuEl,
        }));
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
        ];
    }

    async onInput() {
        if (!this.limit) {
            log.logic("onInput: autocomplete disabled, limit is 0");
            return;
        }
        if (this.searchType === "all" && !this.inputEl.value.trim().length) {
            log.logic("onInput: empty query on 'all', closing dropdown");
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
                log.logic("onKeydown: Enter, disabling autocomplete for submit");
                this.limit = 0;
                break;
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onSearch(ev) {
        if (this.inputEl.value) {
            log.logic("onSearch: submitting, autocomplete disabled");
            this.limit = 0;
        } else {
            log.logic("onSearch: cleared, closing dropdown");
            this.render();
            ev.preventDefault();
        }
    }
}

registry.category("public.interactions").add("website.search_bar", SearchBar);
