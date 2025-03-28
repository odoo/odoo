import { AddSnippetDialog } from "@web_editor/js/editor/add_snippet_dialog";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(AddSnippetDialog.prototype, {
    /**
     * @override
     * Insert dynamic product snippet by rendering exsisting templates.
     */
    async insertSnippets() {
        const snippetsToDisplay = Array.from(this.props.snippets.values())
            // Note: custom ones have "custom" group, but inner ones (custom or
            // not) have no group.
            .filter(snippet => snippet.group === this.state.groupSelected && !snippet.excluded);

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
                });

                for (const [xmlId, snippets] of Object.entries(data)) {
                    const snippet = snippetsToDisplay.find(
                        (snippet) =>
                            snippet.content[0]?.querySelector("div[data-xml-id]")?.dataset.xmlId === xmlId
                    );

                    if (snippet) {
                        const targetElement = snippet.content[0]?.querySelector("div[data-xml-id]").parentElement;
                        if (targetElement) {
                            targetElement.innerHTML = "";
                            snippets.forEach((snippetHTML) => {
                                const productEl = new DOMParser().parseFromString(
                                    snippetHTML,
                                    "text/html"
                                ).body.firstChild;

                                targetElement.appendChild(productEl);
                            });
                        }
                    }
                }
            }
        }
        super.insertSnippets();
    },
});
