import { LinkPopover } from "@html_editor/main/link/link_popover";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { patch } from "@web/core/utils/patch";
import { useChildRef } from "@web/core/utils/hooks";
import wUtils from "@website/js/utils";
import { useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { CSS_SHORTHANDS } from "@html_builder/utils/utils_css";

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

    onChange() {
        super.onChange();
        Object.assign(this.state.colorsData, this.computeColorsData());
    },

    /**
     * Compute inline styles by applying the given classes to a temporary button
     * inserted in the container.
     *
     * @param {HTMLElement} buttonContainerEl - Container where the temporary
     *                                          button is placed
     * @param {string} variantClass - Variant class (e.g., 'btn-primary')
     * @param {string[]} extraClasses - Extra classes (size, shape)
     *
     * @returns {string} Extracted inline style string
     */
    computeButtonInlineStyles(buttonContainerEl, variantClass, extraClasses) {
        const tempButtonEl = document.createElement("a");
        tempButtonEl.className = `btn ${variantClass} ${extraClasses.join(" ")}`.trim();

        this.props.ignoreDOMMutations(() => buttonContainerEl.appendChild(tempButtonEl));

        const computedStyles = window.getComputedStyle(tempButtonEl);
        const allowedStyles = [
            "color",
            "font-size",
            "font-weight",
            "text-transform",
            "background-color",
            ...CSS_SHORTHANDS["padding"],
            ...CSS_SHORTHANDS["border-width"],
            ...CSS_SHORTHANDS["border-color"],
            ...CSS_SHORTHANDS["border-style"],
            ...CSS_SHORTHANDS["border-radius"],
        ];
        const inlineStyle = [];

        for (const style of allowedStyles) {
            const value = computedStyles.getPropertyValue(style);
            if (value) {
                inlineStyle.push(`${style}: ${value};`);
            }
        }

        this.props.ignoreDOMMutations(() => tempButtonEl.remove());
        return inlineStyle.join("");
    },

    /**
     * Override `computeColorsData` to ensure link style previews (for primary
     * and secondary buttons) in the popover use the actual button styles based
     * on the editing element's classes or component state.
     */
    computeColorsData() {
        const colors = super.computeColorsData();
        if (!this.props.allowCustomStyle) {
            return colors;
        }

        let buttonContainerEl = this.props.containerElement;
        let stylePrefix = "btn";
        let sizeClasses = [];
        let shapeClasses = [];

        const stylePrefixRegex = /(outline|fill)/;

        if (buttonContainerEl.tagName === "A") {
            sizeClasses = [...buttonContainerEl.classList].filter((cls) =>
                ["btn-lg", "btn-sm"].includes(cls)
            );
            shapeClasses = [...buttonContainerEl.classList].filter((cls) =>
                ["flat", "rounded-circle"].includes(cls)
            );

            const prefix = buttonContainerEl.className.match(stylePrefixRegex)?.[0];
            if (prefix) {
                stylePrefix = `btn-${prefix}`;
            }

            buttonContainerEl = buttonContainerEl.parentElement;
        } else if (this.state) {
            const { buttonShape = "", buttonSize = "" } = this.state;

            const prefix = buttonShape.match(stylePrefixRegex)?.[0];
            stylePrefix = prefix ? `btn-${prefix}` : "btn";

            if (buttonSize) {
                sizeClasses.push(`btn-${buttonSize}`);
            }

            shapeClasses.push(
                ...buttonShape.split(" ").filter((cls) => ["rounded-circle", "flat"].includes(cls))
            );
        }

        const extraClasses = [...sizeClasses, ...shapeClasses];

        const primaryClass = `${stylePrefix}-primary`;
        const secondaryClass = `${stylePrefix}-secondary`;

        const applyStyle = (btnType, variantClass) => {
            const index = colors.findIndex((color) => color.type === btnType);
            if (index !== -1) {
                colors[index].style = this.computeButtonInlineStyles(
                    buttonContainerEl,
                    variantClass,
                    extraClasses
                );
            }
        };

        applyStyle("primary", primaryClass);
        applyStyle("secondary", secondaryClass);

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
