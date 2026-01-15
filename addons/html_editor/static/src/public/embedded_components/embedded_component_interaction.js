import { TableOfContentManager } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";
import { Component, onMounted, onWillDestroy, useSubEnv, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { Interaction } from "@web/public/interaction";
import { PUBLIC_EMBEDDINGS } from "@html_editor/public/embedding_sets";

class EmbeddedDummy extends Component {
    static template = xml``;
    static props = ["*"];
}

export const getEmbeddingMap = memoize(
    (embeddings) => new Map(embeddings.map((embedding) => [embedding.name, embedding]))
);

const getTocManager = memoize((element) => new TableOfContentManager({ el: element }));

/**
 * Mount EmbeddedComponent in the Knowledge public view.
 */
export class EmbeddedComponentInteraction extends Interaction {
    static selector = "[data-embedded]";

    dynamicContent = {
        _root: {
            "t-component": () => {
                const embedding = this.getEmbedding(this.el.dataset.embedded) ?? {
                    Component: EmbeddedDummy,
                };
                return this.getComponentInfo(embedding);
            },
        },
    };

    getComponentInfo({ Component: ComponentClass, getEditableDescendants, getProps, name }) {
        if (ComponentClass === EmbeddedDummy) {
            return [ComponentClass, {}];
        }
        const host = this.el;
        const interactionsService = this.services["public.interactions"];
        ComponentClass = class extends ComponentClass {
            setup() {
                useSubEnv(subEnv);
                super.setup();
                onMounted(() => {
                    for (const node of [...host.childNodes]) {
                        // Ensure that only OWL renderings are kept inside
                        // the host when the component is alive.
                        if (node.nodeName !== "OWL-ROOT") {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                interactionsService.stopInteractions(node);
                            }
                            node.remove();
                        }
                    }
                });
                onWillDestroy(() => {
                    // Ensure that editableDescendants are kept inside the
                    // host in case the component should be mounted again later.
                    const editableDescendants = getEditableDescendants?.(host) ?? {};
                    host.append(...Object.values(editableDescendants));
                });
            }
        };
        const subEnv = {};
        if (getEditableDescendants) {
            subEnv.getEditableDescendants = getEditableDescendants;
        }
        const props = {
            ...(getProps?.(host) || {}),
        };
        this.setupNewComponent({ name: name, env: subEnv, props });
        return [ComponentClass, props];
    }

    getEmbedding(name) {
        return getEmbeddingMap(PUBLIC_EMBEDDINGS).get(name);
    }

    setupNewComponent({ name, env, props }) {
        if (name === "tableOfContent") {
            Object.assign(props, {
                // Define the TOC scope to its siblings.
                manager: getTocManager(this.el.parentElement),
            });
        }
    }
}

registry
    .category("public.interactions")
    .add("html_editor.embedded_component", EmbeddedComponentInteraction);
