/** @odoo-module native */
import { LinkPopover } from "@html_editor/main/link/link_popover";
import { useEffect } from "@odoo/owl";
import { AutoComplete } from "@web/components/autocomplete";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { useChildRef } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { loadAnchors } from "@website/js/utils";

const log = makeLogger("website.editor.html_editor");

export class AutoCompleteInLinkPopover extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        inputClass: { type: String, optional: true },
        updateValue: { type: Function, optional: true },
    };
    static template = "website.AutoCompleteInLinkPopover";

    get autoCompleteRootClass() {
        return `${super.autoCompleteRootClass} col`;
    }

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

patch(LinkPopover.prototype, {
    setup() {
        super.setup();
        useLifecycleLog(log);
        this.urlRef = useChildRef();
        useEffect(
            (el) => {
                if (
                    el &&
                    (this.state.isImage || (!this.state.url && this.state.label))
                ) {
                    el.focus();
                }
            },
            () => [this.urlRef.el],
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
            log.logic("loadOptionsSource: anchor term", () => ({ term }));
            const endAnchors = log.perf("loadOptionsSource loadAnchors");
            const anchors = await loadAnchors(
                term,
                this.props.linkElement.ownerDocument.body,
            );
            endAnchors({ anchors: anchors.length });
            return anchors.map(
                (anchor) => makeItem({ label: anchor, value: anchor }),
                this,
            );
        } else if (term.startsWith("http") || term.length === 0) {
            log.logic(
                "loadOptionsSource: absolute or empty term, no suggestions",
                () => ({
                    term,
                }),
            );
            return [];
        }

        const endSuggest = log.perf("loadOptionsSource get_suggested_links", () => ({
            term,
        }));
        const res = await rpc("/website/get_suggested_links", {
            needle: term,
            limit: 15,
        });
        endSuggest(() => ({
            pages: res.matching_pages.length,
            others: res.others.length,
        }));
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
        log.pipeline("loadOptionsSource: choices built", () => ({
            term,
            choices: choices.length,
        }));
        return choices;
    },

    onSelect(value) {
        log.logic("onSelect", () => ({ value, isImage: this.state.isImage }));
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
                new RegExp(`^https?://${session.db}\\.odoo\\.com(/.*)?$`).test(
                    parsedUrl.origin,
                )) &&
            !parsedUrl.pathname.startsWith("/odoo") &&
            !parsedUrl.pathname.startsWith("/web") &&
            !parsedUrl.pathname.startsWith("/@/")
        );
    },
    onClickForcePreviewMode(ev) {
        if (this.props.linkElement.href) {
            const currentUrl = new URL(this.props.linkElement.href);
            if (
                this.isFrontendUrl(browser.location.href) &&
                this.isFrontendUrl(this.props.linkElement.href)
            ) {
                log.logic(
                    "onClickForcePreviewMode: open frontend url in preview",
                    () => ({
                        href: this.props.linkElement.href,
                    }),
                );
                ev.preventDefault();
                currentUrl.pathname = `/@${currentUrl.pathname}`;
                browser.open(currentUrl);
            }
        }
    },
});
