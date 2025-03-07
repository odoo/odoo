import { patch } from "@web/core/utils/patch";
import { AddSnippetDialog } from "@web_editor/js/editor/add_snippet_dialog";
import { rpc } from "@web/core/network/rpc";

patch(AddSnippetDialog.prototype, {
    /**
     * 
     * @override
     * Inserts the snippets from the selected snippetGroup into the <iframe>.
     * 
     */
    async insertSnippets() {
        const snippetsToDisplay = [...this.props.snippets.values()]
            .filter((snippet) => {
                // Note: custom ones have "custom" group, but inner ones (custom or
                // not) have no group.
                return !snippet.excluded && snippet.group;
            })
            .filter((snippet) => snippet.group === this.state.groupSelected);

        if (this.state.groupSelected === "products") {
            const xmlIdToElementsMap = snippetsToDisplay.reduce((acc, snippet) => {
                const xmlId = snippet.content[0]?.querySelector("div[data-xml-id]")?.dataset.xmlId;
                const numberOfElements = parseInt(snippet.data.numberOfElements) || 4;
                if (xmlId) {
                    acc[xmlId] = numberOfElements;
                }
                return acc;
            }, {});

            if (Object.keys(xmlIdToElementsMap).length) {
                const data = await rpc("/website_sale/get_snippet_data", {
                    template_data: xmlIdToElementsMap,
                    csrf_token: odoo.csrf_token,
                });

                for (const [xmlId, snippets] of Object.entries(data)) {
                    const snippet = snippetsToDisplay.find(
                        (snippet) =>
                            snippet.content[0]?.querySelector("div[data-xml-id]")?.dataset.xmlId === xmlId
                    );

                    if (snippet) {
                        const fragment = document.createDocumentFragment();

                        snippets.forEach((snippetHTML) => {
                            const productEl = new DOMParser().parseFromString(
                                snippetHTML,
                                "text/html"
                            ).body.firstChild;

                            fragment.appendChild(productEl);
                        });

                        const targetElement = snippet.content[0]?.querySelector("div[data-xml-id]");
                        if (targetElement) {
                            targetElement.replaceWith(fragment);
                        }
                    }
                }
            }
        }
        super.insertSnippets();
    },
});
