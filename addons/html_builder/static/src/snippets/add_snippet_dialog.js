import { onWillRender, useRef, useState } from "@web/owl2/utils";
import { Component, onWillUnmount, useEffect } from "@odoo/owl";
import { loadBundle, loadCSS } from "@web/core/assets";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { localization } from "@web/core/l10n/localization";
import { getFirstAndLastTabableElements } from "@web/core/ui/ui_service";
import { cookie } from "@web/core/browser/cookie";
import { useChildRef } from "@web/core/utils/hooks";
import { SnippetViewer } from "./snippet_viewer";

/**
 * @typedef {((arg: { iframe: HTMLIFrameElement }) => void)[]} snippet_preview_dialog_stylesheets_processors
 * @typedef {string[]} snippet_preview_dialog_bundles
 */

export class AddSnippetDialog extends Component {
    static template = "html_builder.AddSnippetDialog";
    static components = { Dialog };
    static props = {
        selectedSnippet: { type: Object },
        selectSnippet: { type: Function },
        snippetModel: { type: Object },
        close: { type: Function },
        installSnippetModule: { type: Function },
        editor: { type: Object },
    };

    setup() {
        this.pcIframeRef = useRef("pcIframe");
        this.mobIframe0Ref = useRef("mobIframe0");
        this.mobIframe1Ref = useRef("mobIframe1");
        this.mobIframe2Ref = useRef("mobIframe2");
        this.modalRef = useChildRef();
        this.state = useState({
            search: "",
            groupSelected: this.props.selectedSnippet.groupName,
            showIframe: false,
            hasNoSearchResults: false,
            isMobilePreviewSnippet: false,
        });
        this.snippetViewerProps = {
            state: this.state,
            hasSearchResults: (has) => {
                this.state.hasNoSearchResults = !has;
            },
            selectSnippet: (...args) => {
                this.props.selectSnippet(...args);
                this.props.close();
            },
            snippetModel: this.props.snippetModel,
            installSnippetModule: this.props.installSnippetModule,
            frontendDirection: this.props.editor.editable.classList.contains("o_rtl")
                ? "rtl"
                : "ltr",
        };

        this.roots = [];

        useEffect(
            (isMobile) => {
                this.state.showIframe = false;

                const iframes = isMobile
                    ? [this.mobIframe0Ref.el, this.mobIframe1Ref.el, this.mobIframe2Ref.el]
                    : [this.pcIframeRef.el];
                this.initIframes(iframes, isMobile).then(() => {
                    this.state.showIframe = true;
                });
            },
            () => [this.state.isMobilePreviewSnippet]
        );

        onWillRender(() => {
            if (!this.props.snippetModel.hasCustomGroup && this.state.groupSelected === "custom") {
                this.state.groupSelected = this.props.snippetModel.snippetGroups[0].groupName;
            }
        });

        onWillUnmount(() => {
            this.destroyRoots();
        });
    }

    destroyRoots() {
        if (this.roots) {
            for (const root of this.roots) {
                root.destroy();
            }
        }
    }

    async initIframes(iframes, isMobile) {
        const isFirefox = isBrowserFirefox();
        if (isFirefox && !(this.iframeRef.el?.contentDocument.readyState === "complete")) {
            // Make sure empty preview iframe is loaded.This was necessary
            // in Firefox < 148 as it created and parsed a new document.
            // This event is never triggered on Chrome.
            await new Promise((resolve) => {
                this.iframeRef.el.addEventListener("load", resolve, { once: true });
            });
        }
        for (let i = 0; i < iframes.length; i++) {
            const iframe = iframes[i];
            const iframeDocument = iframe.contentDocument;
            iframeDocument.body.parentElement.classList.add("o_add_snippets_preview");
            iframeDocument.body.style.setProperty("direction", localization.direction);
            iframeDocument.body.tabIndex = "-1";
            iframeDocument.addEventListener("keydown", this.onIframeDocumentKeydown.bind(this));
            const props = { ...this.snippetViewerProps };
            if (isMobile) {
                props.mobileColumnIndex = i;
                iframeDocument.querySelector("html").classList.add("o_is_mobile_preview");
                iframeDocument.body.style.width = "100%";
                iframeDocument.body.style.height = "100%";
            }
            const root = this.__owl__.app.createRoot(SnippetViewer, {
                props: props,
            });
            this.roots.push(root);
            root.mount(iframeDocument.body);
        }
        await Promise.all(iframes.map((iframe) => this.insertStyle(iframe)));
        for (const iframe of iframes) {
            this.insertColorScheme(iframe);
        }
    }

    /**
     * Allow to insert content inside the Iframe's head
     */
    renderIframeHead() {}

    /**
     * Loads and injects the required styles into the iframe's <head>.
     * The URL for web.assets_frontend CSS bundle is retrieved from the editor
     * document to ensure consistency, especially when using the RTL version.
     */
    async insertStyle(iframe) {
        const loadCSSBundleFromEditor = (bundleName, loadOptions) => {
            const cssLinkEl = this.props.editor.document.head.querySelector(
                `link[type="text/css"][href*="/${bundleName}."]`
            );
            if (cssLinkEl) {
                return loadCSS(cssLinkEl.getAttribute("href"), loadOptions);
            }
            return loadBundle(bundleName, loadOptions);
        };
        this.props.editor.processThrough("snippet_preview_dialog_stylesheets_processors", {
            iframe: iframe,
        });
        const editorPreviewAssetsBundles = this.props.editor.getResource(
            "snippet_preview_dialog_bundles"
        );
        const loadOptions = { targetDoc: iframe.contentDocument, js: false };
        await Promise.all([
            ...editorPreviewAssetsBundles.map((assetsBundle) =>
                loadCSSBundleFromEditor(assetsBundle, loadOptions)
            ),
            ...this.getDefaultAssets().map((assetName) => loadBundle(assetName, loadOptions)),
        ]);
    }

    getDefaultAssets() {
        return ["html_builder.iframe_add_dialog"];
    }

    get snippetGroups() {
        return this.props.snippetModel.snippetGroups.filter(
            (snippetGroup) => !snippetGroup.moduleId
        );
    }

    toggleMobilePreviewSnippet() {
        this.state.isMobilePreviewSnippet = !this.state.isMobilePreviewSnippet;
    }

    selectGroup(snippetGroup) {
        this.state.groupSelected = snippetGroup.groupName;
        const iframes = this.state.isMobilePreviewSnippet
            ? [this.mobIframe0Ref.el, this.mobIframe1Ref.el, this.mobIframe2Ref.el]
            : [this.pcIframeRef.el];
        for (const iframe of iframes) {
            iframe.contentDocument.body.scrollTop = 0;
        }
    }

    /**
     * Retrieves the color-scheme cookie and injects it into the iframe's
     * <head> and add a custom class. This is necessary to allow the dark mode
     * to be handled correctly across browsers.
     */
    insertColorScheme(iframe) {
        const colorScheme = cookie.get("color_scheme") || "light";
        const metaElement = document.createElement("meta");
        const iframeDocument = iframe.contentDocument;
        metaElement.setAttribute("name", "color-scheme");
        metaElement.content = colorScheme;
        iframeDocument.head.appendChild(metaElement);
        iframeDocument.body.parentElement.classList.add("o_add_snippets_preview--" + colorScheme);
    }

    /**
     * Handles the tablist navigation.
     *
     * @param {KeyboardEvent} ev
     */
    onTabKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (!["arrowleft", "arrowright", "arrowdown", "arrowup"].includes(hotkey)) {
            return;
        }
        if (["arrowleft", "arrowup"].includes(hotkey)) {
            ev.currentTarget.previousElementSibling?.focus();
        } else {
            ev.currentTarget.nextElementSibling?.focus();
        }
    }
    /**
     * The mix of focused elements within the dialog and within the iframe does
     * not work well with the `useActiveElement` standard focus trap. This
     * listener ensures the cycle is well supported.
     *
     * @param {KeyboardEvent} ev
     */
    onIframeDocumentKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (!["tab", "shift+tab"].includes(hotkey)) {
            return;
        }
        const [, lastTabableElInIframe] = getFirstAndLastTabableElements(ev.currentTarget);
        if (hotkey === "tab" && lastTabableElInIframe === ev.target) {
            const [firstTabableElInDialog] = getFirstAndLastTabableElements(this.modalRef.el);
            firstTabableElInDialog.focus();
            ev.preventDefault();
            ev.stopPropagation();
        } else if (hotkey === "shift+tab" && ev.target.tagName === "BODY") {
            lastTabableElInIframe.focus();
            ev.preventDefault();
            ev.stopPropagation();
        }
    }
}
