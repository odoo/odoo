import { Component, onMounted, onWillDestroy, onWillRender, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
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
    };

    setup() {
        this.iframeRef = useRef("iframe");

        this.state = useState({
            search: "",
            groupSelected: this.props.selectedSnippet.groupName,
            showIframe: false,
        });
        this.snippetViewerProps = {
            state: this.state,
            selectSnippet: (...args) => {
                this.props.selectSnippet(...args);
                this.props.close();
            },
            snippetModel: this.props.snippetModel,
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

            await loadBundle("html_builder.iframe_add_dialog", {
                targetDoc: iframeDocument,
                js: false,
            });
            this.state.showIframe = true;
        });

        onWillRender(() => {
            if (!this.props.snippetModel.hasCustomGroup && this.state.groupSelected === "custom") {
                this.state.groupSelected = this.props.snippetModel.snippetGroups[0].groupName;
            }
        });

        onWillDestroy(() => {
            root.destroy();
        });
    }

    get snippetGroups() {
        return this.props.snippetModel.snippetGroups.filter(
            (snippetGroup) => !snippetGroup.moduleId
        );
    }

    selectGroup(snippetGroup) {
        this.state.groupSelected = snippetGroup.groupName;
    }
}
