import { Component, onMounted, onWillUnmount, onWillRender, useRef, useState } from "@odoo/owl";
import { loadBundle, loadCSS } from "@web/core/assets";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { localization } from "@web/core/l10n/localization";
import { SnippetViewer } from "./snippet_viewer";

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
        this.iframeRef = useRef("iframe");
        this.state = useState({
            search: "",
            groupSelected: this.props.selectedSnippet.groupName,
            showIframe: false,
            hasNoSearchResults: false,
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

        let root;
        onMounted(async () => {
            const isFirefox = isBrowserFirefox();
            if (isFirefox) {
                // Make sure empty preview iframe is loaded.
                // This event is never triggered on Chrome.
                await new Promise((resolve) => {
                    this.iframeRef.el.addEventListener("load", resolve, { once: true });
                });
            }

            const iframeDocument = this.iframeRef.el.contentDocument;
            iframeDocument.body.parentElement.classList.add("o_add_snippets_preview");
            iframeDocument.body.style.setProperty("direction", localization.direction);

            root = this.__owl__.app.createRoot(SnippetViewer, {
                props: this.snippetViewerProps,
            });
            root.mount(iframeDocument.body);

            await this.insertStyle();
            this.state.showIframe = true;
        });

        onWillRender(() => {
            if (!this.props.snippetModel.hasCustomGroup && this.state.groupSelected === "custom") {
                this.state.groupSelected = this.props.snippetModel.snippetGroups[0].groupName;
            }
        });

        onWillUnmount(() => {
            root.destroy();
        });
    }

    /**
     * Loads and injects the required styles into the iframe's <head>.
     * The URL for web.assets_frontend CSS bundle is retrieved from the editor
     * document to ensure consistency, especially when using the RTL version.
     */
    async insertStyle() {
        const loadCSSBundleFromEditor = (bundleName, loadOptions) => {
            const cssLinkEl = this.props.editor.document.head.querySelector(
                `link[type="text/css"][href*="/${bundleName}."]`
            );
            if (cssLinkEl) {
                return loadCSS(cssLinkEl.getAttribute("href"), loadOptions);
            }
            return loadBundle(bundleName, loadOptions);
        };
        this.props.editor.dispatchTo("snippet_preview_dialog_stylesheets_handlers", {
            iframe: this.iframeRef.el,
        });
        const loadOptions = { targetDoc: this.iframeRef.el.contentDocument, js: false };
        await Promise.all([
            loadCSSBundleFromEditor("web.assets_frontend", loadOptions),
            loadBundle("html_builder.iframe_add_dialog", loadOptions),
        ]);
    }

    get snippetGroups() {
        return this.props.snippetModel.snippetGroups.filter(
            (snippetGroup) => !snippetGroup.moduleId
        );
    }

    selectGroup(snippetGroup) {
        this.state.groupSelected = snippetGroup.groupName;
        const iframeDocument = this.iframeRef.el.contentDocument;
        iframeDocument.body.scrollTop = 0;
    }
}
