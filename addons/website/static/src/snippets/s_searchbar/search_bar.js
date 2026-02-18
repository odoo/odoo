import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { getTemplate } from "@web/core/templates";
import { KeepLast } from "@web/core/utils/concurrency";
import { utils as ui } from "@web/core/ui/ui_service";
import { _t } from "@web/core/l10n/translation";

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
            "t-on-click": this.removeKeyboardNavigation,
        },
        ".o_search_result_item a": {
            "t-on-keydown": this.onKeydown,
        },
        ".o_search_input_group": {
            "t-on-click": this.switchInputToModal,
        },
    };
    autocompleteMinWidth = 300;

    setup() {
        this.keepLast = new KeepLast();
        this.inputEl = this.el.querySelector(".search-query");
        this.buttonEl = this.el.querySelector(".oe_search_button");
        this.actionEl = this.buttonEl.querySelector(".o_search_found_results_action");
        this.resultsEl = this.buttonEl.querySelector(".o_search_found_results");
        this.iconEl = this.buttonEl.querySelector(".oi-search");
        this.spinnerEl = this.buttonEl.querySelector(".o_search_spinner");
        this.searchInputGroup = this.el.querySelector(".o_search_input_group");
        this.initialInputValue = this.inputEl.value;
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
            proportionate_allocation: true,
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
                },
                this.el
            )[0];
            this.updateSearchCount(res.results_count || 0);
        } else {
            this.clearButtonContent();
        }
        this.hasDropdown = !!res;
        prevMenuEl?.remove();
    }

    clearButtonContent() {
        this.hideLoadingSpinner();
        const isEmpty = !this.inputEl.value.trim();
        this.buttonEl.disabled = true;
        this.actionEl?.classList.add("d-none");
        // If empty, only show icon; otherwise show results
        this.resultsEl?.classList.toggle("d-none", isEmpty);
        this.iconEl?.classList.toggle("d-none", !isEmpty);
    }

    /**
     * @param {number} count
     */
    updateSearchCount(count) {
        this.hideLoadingSpinner();
        this.buttonEl.toggleAttribute("disabled", count === 0);
        const countText = count <= 1 ? _t("%s result", count) : _t("%s results", count);
        for (const el of this.buttonEl.querySelectorAll(".o_search_count")) {
            el.textContent = countText;
        }

        const hasLiveResults = count > 0 && this.inputEl.value !== this.initialInputValue;
        this.actionEl?.classList.toggle("d-none", !hasLiveResults);
        this.buttonEl.toggleAttribute("disabled", !hasLiveResults);
        this.resultsEl?.classList.toggle("d-none", hasLiveResults);
        this.iconEl?.classList.add("d-none");
    }

    hideLoadingSpinner() {
        this.spinnerEl?.classList.add("d-none");
    }

    showLoadingSpinner() {
        this.actionEl?.classList.add("d-none");
        this.resultsEl?.classList.add("d-none");
        this.iconEl?.classList.add("d-none");
        this.spinnerEl?.classList.remove("d-none");
    }

    getFieldsNames() {
        return ["body", "description", "name", "search_item_metadata", "tags"];
    }

    async onInput() {
        if (!this.limit) {
            return;
        }
        // If the input is empty, we render the initial state
        const value = this.inputEl.value.trim();
        if (!value.length) {
            this.render();
        } else {
            this.showLoadingSpinner();
            if (!this.hasDropdown) {
                this.renderLoading();
            }
            const res = await this.keepLast.add(this.waitFor(this.fetch()));
            this.render(res);
        }
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
            case "Tab":
                this.el.classList.add("o_keyboard_navigation");
                break;
        }
    }

    removeKeyboardNavigation() {
        this.el.classList.remove("o_keyboard_navigation");
    }

    focusInput() {
        this.inputEl.classList.remove("pe-none");
        this.inputEl.focus();
    }

    switchInputToModal(ev) {
        if (ev.target.closest(".oe_search_button")) {
            return;
        }
        if (this.searchInputGroup.hasAttribute("data-search-modal-id")) {
            const modalId = "#" + this.searchInputGroup.dataset.searchModalId;
            const forceModalTrigger = this.searchInputGroup.hasAttribute(
                "data-force-modal-trigger"
            );
            if (
                ui.isSmall() ||
                this.searchInputGroup.getBoundingClientRect().width < 280 ||
                forceModalTrigger
            ) {
                this.searchInputGroup.setAttribute("data-bs-toggle", "modal");
                this.searchInputGroup.setAttribute("data-bs-target", modalId);
                this.inputEl.classList.add("pe-none");

                // Add hidden inputs to modal
                const modelEl = document.querySelector(modalId + " form");
                modelEl.querySelectorAll("input[type=hidden]").forEach((el) => el.remove());
                const hiddenInputEls = this.el.querySelectorAll("input[type=hidden]");
                hiddenInputEls.forEach((el) => {
                    const clone = el.cloneNode(true);
                    modelEl.appendChild(clone);
                });

                this.searchInputGroup.click();
            } else {
                this.searchInputGroup.removeAttribute("data-bs-toggle");
                this.searchInputGroup.removeAttribute("data-bs-target");
                this.focusInput();
            }
        } else {
            this.focusInput();
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
