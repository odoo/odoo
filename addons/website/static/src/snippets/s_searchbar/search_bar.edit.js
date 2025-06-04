import { SearchBar } from "@website/snippets/s_searchbar/search_bar";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";
import { MacroMutationObserver } from "@web/core/macro";

const SearchBarEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                "t-on-click": this.debounced(this.onClick, 100),
            },
        };
        start() {
            super.start();
            this.inputEl = this.el.querySelector(".search-query");
            this.isDropdownVisible = false;
            this.websiteEditService = this.services.website_edit;
            this.observedState = {
                templateId: this.inputEl.dataset.templateId,
                displayDescription: this.inputEl.dataset.displayDescription,
                displayImage: this.inputEl.dataset.displayImage,
                displayExtraLink: this.inputEl.dataset.displayExtraLink,
                displayDetail: this.inputEl.dataset.displayDetail,
            };
        }
        temp() {
            this.templateObserver = new MacroMutationObserver(() => {
                const newState = {
                    templateId: this.inputEl.dataset.templateId,
                    displayDescription: this.inputEl.dataset.displayDescription,
                    displayImage: this.inputEl.dataset.displayImage,
                    displayExtraLink: this.inputEl.dataset.displayExtraLink,
                    displayDetail: this.inputEl.dataset.displayDetail,
                };

                const hasChanged = Object.keys(newState).some(
                    (key) => newState[key] !== this.observedState[key]
                );

                if (hasChanged && this.isDropdownVisible) {
                    this.observedState = newState;
                    this.render();
                }
            });
        }
        onClick() {
            this.websiteEditService.callShared("history", "ignoreDOMMutations", () => {
                if (!this.isDropdownVisible) {
                    this.render();
                }
                if (this.templateObserver) {
                    this.templateObserver.disconnect();
                    this.templateObserver = null;
                }
                this.temp();

                this.observedState = {
                    templateId: this.inputEl.dataset.templateId,
                    displayDescription: this.inputEl.dataset.displayDescription,
                    displayImage: this.inputEl.dataset.displayImage,
                    displayExtraLink: this.inputEl.dataset.displayExtraLink,
                    displayDetail: this.inputEl.dataset.displayDetail,
                };

                this.templateObserver.observe(this.inputEl, {
                    attributes: true,
                    attributeFilter: [
                        "data-template-id",
                        "data-display-description",
                        "data-display-image",
                        "data-display-extra-link",
                        "data-display-detail",
                    ],
                });
                this.inputEl = this.el.querySelector(".search-query");

                // Bind the document click handler
                this.onDocumentClick = this.handleDocumentClick.bind(this);
                window.addEventListener("click", this.onDocumentClick);
            });
        }
        handleDocumentClick(ev) {
            if (this.isDropdownVisible) {
                const clickedInside = this.el.contains(ev.target);
                if (!clickedInside) {
                    this.hideDropdown();
                }
            }
        }
        hideDropdown() {
            if (this.menuEl) {
                this.menuEl.remove();
                this.menuEl = null;
            }
            if (this.templateObserver) {
                this.templateObserver.disconnect();
                this.templateObserver = null;
            }
            this.isDropdownVisible = false;
            window.removeEventListener("click", this.onDocumentClick);
        }
        getResults(displayImage) {
            return [
                {
                    attributes: "AA: Wooden",
                    barcode: "1111225331",
                    colors: "Red",
                    default_code: "None",
                    description: "Description",
                    detail: markup("$ 252.0"),
                    detail_strike: markup("$ 280.0"),
                    extra_link: "Category",
                    image_url: displayImage === "true",
                    name: markup('<span class="text-primary-emphasis">Dum</span><span>my</span>'),
                    "product_variant_ids.default_code": "None",
                    rating: "3",
                    website_url: "#",
                    _fa: displayImage === "true",
                },
            ];
        }

        getParts({ displayDescription, displayImage, displayExtraLink, displayDetail }) {
            return {
                attributes: true,
                barcode: true,
                body: true,
                colors: true,
                default_code: true,
                description: displayDescription === "true",
                detail: displayDetail === "true",
                detail_strike: true,
                extra_link: displayExtraLink === "true",
                icon: displayImage === "true",
                image_url: displayImage === "true",
                name: true,
                "product_variant_ids.default_code": true,
                rating: true,
                website_url: true,
            };
        }

        getWidgetConfig() {
            return {
                allowFuzzy: true,
                displayDescription: "true",
                displayDetail: "true",
                displayExtraLink: "true",
                displayImage: "true",
                order: "name asc",
            };
        }
        render() {
            this.websiteEditService.callShared("history", "ignoreDOMMutations", () => {
                if (this.menuEl) {
                    this.menuEl.remove();
                    this.menuEl = null;
                }
                if (document.querySelector(".o_dropdown_menu")) {
                    document.querySelector(".o_dropdown_menu").remove();
                }
                const {
                    templateId,
                    displayDescription,
                    displayImage,
                    displayExtraLink,
                    displayDetail,
                } = this.observedState;
                if (!templateId) {
                    return;
                }
                this.menuEl = this.renderAt(
                    templateId,
                    {
                        results: this.getResults(displayImage),
                        parts: this.getParts({
                            displayDescription,
                            displayImage,
                            displayExtraLink,
                            displayDetail,
                        }),
                        hasMoreResults: false,
                        search: "war",
                        fuzzySearch: false,
                        widget: this.getWidgetConfig(),
                    },
                    this.el
                )[0];
                this.isDropdownVisible = true;
            });
        }
        destroy() {
            if (this.menuEl) {
                this.menuEl.remove();
                this.menuEl = null;
            }
            if (this.templateObserver) {
                this.templateObserver.disconnect();
                this.templateObserver = null;
            }
            this.isDropdownVisible = false;
            window.removeEventListener("click", this.onDocumentClick);
        }
    };

registry.category("public.interactions.edit").add("website.search_bar", {
    Interaction: SearchBar,
    mixin: SearchBarEdit,
});
