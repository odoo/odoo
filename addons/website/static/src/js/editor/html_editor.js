import { LinkPopover } from "@html_editor/main/link/link_popover";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { patch } from "@web/core/utils/patch";
import { useChildRef } from "@web/core/utils/hooks";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import wUtils from "@website/js/utils";
import { useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

/**
 * The goal of this patch is to handle the URL autocomplete in the LinkPopover
 * component. The URL autocomplete is used to suggest internal links, anchors.
 * Before, the autocomplete was implemented as another OWL app. Now with this
 * patch, URL autocomplete is implemented as a child component.
 */

/**
 * this class is used to create a new autocomplete component that will be used
 * in the LinkPopover component. Similar with AutoCompleteWithPages but it has
 * two new props:
 * - inputClass: to change the style of the input element in autocomplete
 * - updateValue: to update the URL of the link element
 */
export class AutoCompleteInLinkPopover extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        inputClass: { type: String, optional: true },
        updateValue: { type: Function, optional: true },
    };
    static template = "website.AutoCompleteInLinkPopover";

    // overwrite the div class to avoid breaking the popover style
    get autoCompleteRootClass() {
        return `${super.autoCompleteRootClass} col`;
    }

    // apply classes on the input element in autocomplete
    get inputClass() {
        return this.props.inputClass || "o_input pe-3";
    }

    /**
     * @override
     */
    onInput() {
        super.onInput();
        this.props.updateValue(this.targetDropdown.value);
    }
}

patch(LinkPopover, {
    components: { ...LinkPopover.components, AutoCompleteInLinkPopover },
});

/* patch the LinkPopover component to maintain the option source for the
 * AutoCompleteInLinkPopover component. Also we make sure state.url is updated
 * when the user enters text in the autocomplete and selects an option from the
 * autocomplete.
 */
patch(LinkPopover.prototype, {
    setup() {
        super.setup();
        this.urlRef = useChildRef();
        useEffect(
            (el) => {
                if (el && (this.state.isImage || (!this.state.url && this.state.label))) {
                    el.focus();
                }
            },
            () => [this.urlRef.el]
        );
    },

    get sources() {
        return [this.optionsSource];
    },

    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
            optionSlot: "urlOption",
        };
    },

    async loadOptionsSource(term) {
        const makeItem = (item) => ({
            cssClass: "ui-autocomplete-item",
            label: item.label,
            onSelect: this.onSelect.bind(this, item.value),
            data: { icon: item.icon || false, isCategory: false },
        });

        if (term[0] === "#") {
            const anchors = await wUtils.loadAnchors(
                term,
                this.props.linkElement.ownerDocument.body
            );
            return anchors.map((anchor) => makeItem({ label: anchor, value: anchor }), this);
        } else if (term.startsWith("http") || term.length === 0) {
            // avoid useless call to /website/get_suggested_links
            return [];
        }

        const res = await rpc("/website/get_suggested_links", {
            needle: term,
            limit: 15,
        });
        const choices = [];
        for (const page of res.matching_pages) {
            choices.push(makeItem(page));
        }
        for (const other of res.others) {
            if (other.values.length) {
                choices.push({
                    cssClass: "ui-autocomplete-category",
                    label: other.title,
                    data: { icon: false, isCategory: true },
                });
                for (const page of other.values) {
                    choices.push(makeItem(page));
                }
            }
        }
        return choices;
    },
    /**
     * Override `computeColorsData` to ensure link style previews (for primary
     * and secondary buttons) in the popover use the actual color combination of
     * the editing element.
     */
    computeColorsData() {
        const SPECIAL_BLOCKS = ["Header", "Footer", "Copyright"];
        const DEFAULT_CC = "1";
        const linkEl = this.props.linkElement;

        if (!this.props.allowCustomStyle) {
            return super.computeColorsData();
        }
        /**
         * Get the most relevant color combination number for an element.
         *
         * Logic:
         * - Walks up the DOM tree from the given element.
         * - Priority rules:
         *   1. If an element has a `o_ccX` class, use its number.
         *   2. If element is a special block (`Header`, `Footer`, `Copyright`),
         *      use its CSS variable (`--menu`, `--footer`, `--copyright`).
         * - Tracks two things:
         *   - `closestCcNum`: the first valid number found when traversing
         *                     upward.
         *   - `highestCcNum`: the largest valid number found among all
         *                     ancestors.
         * - Returns the max between closest and highest (so grandparents can
         *   override), or `"1"` as a fallback if none are found.
         *
         * @param {HTMLElement} el - Starting element.
         * @returns {string} Color combination number as a string.
         */
        const getClosestColorCombinationNum = (el) => {
            const getCcNum = (element) => {
                // Case 1: Check if element has o_ccX class
                const ccClass = [...(element.classList || [])].find((cls) => /^o_cc\d+$/.test(cls));
                if (ccClass) {
                    return ccClass.match(/^o_cc(\d+)$/)[1];
                }

                // Case 2: Header / Footer / Copyright with CSS variables
                const dataName = element.dataset?.name;
                if (SPECIAL_BLOCKS.includes(dataName)) {
                    const rootStyles = window.top.getComputedStyle(element);
                    const varMap = {
                        Header: "--menu",
                        Footer: "--footer",
                        Copyright: "--copyright",
                    };
                    return rootStyles.getPropertyValue(varMap[dataName])?.trim() || DEFAULT_CC;
                }

                return null;
            };

            let current = el;
            let closestCcNum = null;
            let highestCcNum = null;

            while (current) {
                const ccNum = getCcNum(current);
                if (ccNum) {
                    const num = parseInt(ccNum);

                    // First cc element we find is the closest
                    if (closestCcNum === null) {
                        closestCcNum = num;
                    }

                    // Keep track of highest numbered
                    if (!highestCcNum || num > highestCcNum) {
                        highestCcNum = num;
                    }
                }
                current = current.parentElement;
            }

            // Return the greater of closest and highest numbered, or fallback to 1
            if (closestCcNum && highestCcNum) {
                return Math.max(closestCcNum, highestCcNum).toString();
            } else if (closestCcNum || highestCcNum) {
                return (closestCcNum || highestCcNum).toString();
            } else {
                return "1";
            }
        };
        const ccNumber = getClosestColorCombinationNum(
            linkEl.isConnected ? linkEl : this.props.containerElement
        );

        const rootStyles = window.getComputedStyle(this.props.document.documentElement);
        const getVar = (key) =>
            getCSSVariableValue(`o-cc${ccNumber}-${key}`, rootStyles).replace(/^'|'$/g, "");

        const colors = super.computeColorsData();

        // Update primary button
        const primaryIndex = colors.findIndex((c) => c.type === "primary");
        if (primaryIndex !== -1) {
            colors[primaryIndex] = {
                ...colors[primaryIndex],
                className: "btn btn-sm",
                style: `background-color: ${getVar("btn-primary")};
                color: ${getVar("btn-primary-text")};
                border: 1px solid ${getVar("btn-primary-border")}`,
            };
        }

        // Update secondary button
        const secondaryIndex = colors.findIndex((c) => c.type === "secondary");
        if (secondaryIndex !== -1) {
            colors[secondaryIndex] = {
                ...colors[secondaryIndex],
                className: "btn btn-sm",
                style: `background-color: ${getVar("btn-secondary")};
                color: ${getVar("btn-secondary-text")};
                border: 1px solid ${getVar("btn-secondary-border")}`,
            };
        }

        return colors;
    },

    onSelect(value) {
        this.state.url = value;
        if (!this.state.isImage) {
            this.onChange();
        }
    },

    updateValue(val) {
        this.state.url = val;
        if (!this.state.isImage) {
            this.onChange();
        }
    },
    isFrontendUrl(url) {
        const parsedUrl = new URL(url);
        return (
            (browser.location.hostname === parsedUrl.hostname ||
                // Also check if the odoo-hosted domain is the current domain of the url
                new RegExp(`^https?://${session.db}\\.odoo\\.com(/.*)?$`).test(parsedUrl.origin)) &&
            !parsedUrl.pathname.startsWith("/odoo") &&
            !parsedUrl.pathname.startsWith("/web") &&
            !parsedUrl.pathname.startsWith("/@/")
        );
    },
    onClickForcePreviewMode(ev) {
        if (this.props.linkElement.href) {
            const currentUrl = new URL(this.props.linkElement.href);
            // only when we are on a frontend page (in website builder) and the link is also a frontend link
            if (
                this.isFrontendUrl(browser.location.href) &&
                this.isFrontendUrl(this.props.linkElement.href)
            ) {
                ev.preventDefault();
                currentUrl.pathname = `/@${currentUrl.pathname}`;
                browser.open(currentUrl);
            }
        }
    },
});
