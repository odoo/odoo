import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { getTemplate } from "@web/core/templates";
import { KeepLast } from "@web/core/utils/concurrency";
import { utils as ui } from "@web/core/ui/ui_service";
import { renderToElement } from "@web/core/utils/render";

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
            "t-on-click": this.removeKeyboardNavigation,
        },
        ".o_search_result_item a": {
            "t-on-keydown": this.onKeydown,
        },
        ".o_search_input_group, a[title='Search']": {
            "t-on-click": this.switchInputToModal,
        },
    };
    autocompleteMinWidth = 300;

    setup() {
        this.keepLast = new KeepLast();
        this.inputEl = this.el.querySelector(".search-query");
        this.buttonEl = this.el.querySelector(".oe_search_button");
        this.resultsEl = this.buttonEl.querySelector(".o_search_found_results");
        this.iconEl = this.buttonEl.querySelector(".oi-search");
        this.spinnerEl = this.buttonEl.querySelector(".o_search_spinner");
        this.searchInputGroup = this.el.querySelector(".o_search_input_group");
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
            proportionateAllocation: true,
            renderTemplate: true,
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

    async fetch() {
        const res = await rpc("/website/snippet/autocomplete", {
            search_type: this.searchType,
            term: this.inputEl.value,
            order: this.order,
            limit: this.limit,
            max_nb_chars: Math.round(
                Math.max(this.autocompleteMinWidth, this.el.clientWidth / 3) * 0.22
            ),
            options: this.options,
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
            const results = res.results;
            let template = "website.s_searchbar.autocomplete";
            const candidate = template + "." + this.searchType;
            if (getTemplate(candidate)) {
                template = candidate;
            }
            this.menuEl = this.renderAt(
                template,
                {
                    results: markup(results),
                    parts: res["parts"],
                    limit: this.limit,
                    search: this.inputEl.value,
                    fuzzySearch: res["fuzzy_search"],
                    widget: this.options,
                },
                this.el
            )[0];
        }
        this.hasDropdown = !!res;
        prevMenuEl?.remove();
    }

    /**
     * @param {number} count
     */
    updateButtonContent(count) {
        this.hideLoadingSpinner();
        this.resultsEl.querySelector(".o_search_count").textContent = count;
    }

    hideLoadingSpinner() {
        this.resultsEl.classList.toggle("d-none", !this.hasDropdown);
        this.iconEl.classList.toggle("d-none", this.hasDropdown);
        this.spinnerEl.classList.add("d-none");
    }

    showLoadingSpinner() {
        this.resultsEl.classList.add("d-none");
        this.iconEl.classList.add("d-none");
        this.spinnerEl.classList.remove("d-none");
    }

    async onInput() {
        if (!this.limit) {
            return;
        }
        // If the input is empty, we render the initial state
        const value = this.inputEl.value.trim();
        let res = null;
        if (value.length) {
            this.showLoadingSpinner();
            if (!this.hasDropdown) {
                this.renderLoading();
            }
            res = await this.keepLast.add(this.waitFor(this.fetch()));
        }
        this.render(res);
        this.updateButtonContent(res?.results_count || 0);
    }

    renderLoading() {
        if (this.menuEl) {
            this.services["public.interactions"].stopInteractions(this.menuEl);
        }
        const prevMenuEl = this.menuEl;
        this.menuEl = this.renderAt(
            "website.s_searchbar.autocomplete.skeleton.loader",
            {},
            this.el
        )[0];
        this.hasDropdown = true;
        prevMenuEl?.remove();
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
                    const focusableEls = [this.inputEl, ...this.menuEl.querySelectorAll("li > a")];
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
            case "Tab":
                this.el.classList.add("o_keyboard_navigation");
                break;
        }
    }

    removeKeyboardNavigation() {
        this.el.classList.remove("o_keyboard_navigation");
    }

    switchInputToModal(ev) {
        if (ev.target.closest(".modal")) {
            return;
        }
        const isTooSmall =
            ui.isSmall() || this.searchInputGroup.getBoundingClientRect().width < 280;
        const forceModalTrigger = this.searchInputGroup.hasAttribute("data-force-modal-trigger");

        if (isTooSmall || forceModalTrigger) {
            this.openSearchModal();
        }
    }

    openSearchModal() {
        const values = {
            action: this.el.getAttribute("action") || undefined,
            placeholder: this.inputEl.getAttribute("placeholder"),
            limit: this.inputEl.dataset.limit,
            order: this.inputEl.dataset.orderBy,
            autocomplete: this.inputEl.getAttribute("autocomplete"),
            searchType: this.inputEl.dataset.searchType,
        };
        const wrapperEl = renderToElement("website.s_searchbar.modal", values);
        const hiddenInputEls = this.el.querySelectorAll("input[type=hidden]");
        hiddenInputEls.forEach((el) => {
            const clone = el.cloneNode(true);
            wrapperEl.querySelector(".o_searchbar_form").appendChild(clone);
        });
        this.insert(wrapperEl, document.body);
        const modal = new Modal(wrapperEl);
        wrapperEl.addEventListener(
            "shown.bs.modal",
            () => {
                const modalInput = wrapperEl.querySelector(".search-query");
                modalInput?.focus();
            },
            { once: true }
        );
        wrapperEl.addEventListener(
            "hidden.bs.modal",
            () => {
                wrapperEl.remove();
            },
            { once: true }
        );
        modal.show();
    }
}

registry.category("public.interactions").add("website.search_bar", SearchBar);
