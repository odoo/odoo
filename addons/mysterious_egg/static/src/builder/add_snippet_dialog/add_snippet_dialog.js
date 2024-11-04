import { Component, onMounted, onWillDestroy, reactive, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { Dialog } from "@web/core/dialog/dialog";
import { SnippetViewer } from "./snippet_viewer";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";

export class AddSnippetDialog extends Component {
    static template = "mysterious_egg.AddSnippetDialog";
    static components = { Dialog };

    setup() {
        this.iframeRef = useRef("iframe");

        this.state = useState({
            groupSelected: this.props.selectedSnippet.groupName,
            search: "",
            showIframe: false,
        });
        this.snippetViewerProps = {
            state: reactive({ snippets: [] }),
            selectSnippet: (...args) => {
                this.props.selectSnippet(...args);
                this.props.close();
            },
        };
        this.selectGroup(this.props.selectedSnippet);

        let root;
        onMounted(async () => {
            const isFirefox = isBrowserFirefox();
            const iframeDocument = this.iframeRef.el.contentDocument;
            if (isFirefox) {
                // Make sure empty preview iframe is loaded.
                // This event is never triggered on Chrome.
                await new Promise((resolve) => {
                    iframeDocument.body.onload = resolve;
                });
            }

            root = this.__owl__.app.createRoot(SnippetViewer, {
                props: this.snippetViewerProps,
            });
            root.mount(iframeDocument.body);

            iframeDocument.body.parentElement.classList.add("o_add_snippets_preview");
            iframeDocument.body.style.setProperty("direction", localization.direction);
            await loadBundle("mysterious_egg.iframe_add_dialog", iframeDocument);
            this.state.showIframe = true;
        });

        onWillDestroy(() => {
            root.destroy();
        });
    }

    selectGroup(snippetGroup) {
        this.state.groupSelected = snippetGroup.groupName;
        this.snippetViewerProps.state.snippets = this.props.snippetStructures.filter(
            (snippet) => snippet.groupName === this.state.groupSelected
        );
    }
}
