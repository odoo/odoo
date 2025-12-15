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
