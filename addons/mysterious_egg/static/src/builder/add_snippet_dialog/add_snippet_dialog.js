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
            showIframe: false,
        });
        this.snippetViewerProps = {
            state: reactive({ snippets: this.getSelectedSnippets() }),
            selectSnippet: (...args) => {
                this.props.selectSnippet(...args);
                this.props.close();
            },
        };
        this.selectGroup(this.props.selectedSnippet);

        this.categoryById = {};
        for (const snippetGroup of this.props.snippetGroups) {
            if (snippetGroup.groupName) {
                this.categoryById[snippetGroup.groupName] = snippetGroup;
            }
        }

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

            await loadBundle("mysterious_egg.iframe_add_dialog", iframeDocument);
            this.state.showIframe = true;
        });

        onWillDestroy(() => {
            root.destroy();
        });
    }

    getSelectedSnippets() {
        return this.props.snippetStructures.filter(
            (snippet) => snippet.groupName === this.state.groupSelected
        );
    }

    selectGroup(snippetGroup) {
        this.state.groupSelected = snippetGroup.groupName;
        this.snippetViewerProps.state.snippets = this.getSelectedSnippets();
    }

    onInputSearch(ev) {
        const search = ev.target.value.toLowerCase();
        if (search) {
            const strMatches = (str) => !search || str.toLowerCase().includes(search);
            this.snippetViewerProps.state.snippets = this.props.snippetStructures.filter(
                (snippet) => {
                    return (
                        strMatches(this.categoryById[snippet.groupName].title) ||
                        strMatches(snippet.title) ||
                        strMatches(snippet.keyWords || "")
                    );
                }
            );
            return;
        }
        this.snippetViewerProps.state.snippets = this.getSelectedSnippets();
    }
}
