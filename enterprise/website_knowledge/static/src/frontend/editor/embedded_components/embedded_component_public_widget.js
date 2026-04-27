import { useSubEnv, whenReady } from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";
import { KnowledgePublic } from "@website_knowledge/frontend/knowledge_public_view/knowledge_public_view";
import { KNOWLEDGE_PUBLIC_EMBEDDINGS } from "@website_knowledge/frontend/editor/embedded_components/embedding_sets";
import { memoize } from "@web/core/utils/functions";
import { TableOfContentManager } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";

export const getEmbeddingMap = memoize(
    (embeddings) => new Map(embeddings.map((embedding) => [embedding.name, embedding]))
);

const getTocManager = memoize((element) => new TableOfContentManager({ el: element }));

/**
 * This widget simulates a Colibri Interaction in order to mount embedded
 * components in the Knowledge public view.
 * It depends on `owl` instance stored in `window`, and the
 * `KnowledgePublic` (sidebar) as a base App for its lifecycle (destroy).
 */
export const EmbeddedComponentPublicWidget = publicWidget.Widget.extend({
    selector: ".o_knowledge_public_view_static [data-embedded]",

    start() {
        const self = this;
        return whenReady(() => {
            // Tie the EmbeddedComponent lifecycle to the KnowledgePublic (sidebar)
            // which is always there for a Knowledge public view.
            const app = [...(window.owl?.App.apps || [])].find(
                (owlApp) => owlApp.Root === KnowledgePublic
            );
            if (!app) {
                return;
            }
            const host = this.el;
            const embedding = self.getEmbedding(this.el.dataset.embedded);
            if (!embedding) {
                // Don't do anything if the EmbeddedComponent is unknown.
                return;
            }
            const [ComponentClass, props] = self.getComponentInfo(embedding);
            self.componentRoot = app.createRoot(ComponentClass, { props });
            self.componentRoot.mount(host);
            // Patch mount fiber to hook into the exact call stack where root is
            // mounted (but before). This will remove host children synchronously
            // just before adding the root rendered html.
            const fiber = self.componentRoot.node.fiber;
            const fiberComplete = fiber.complete;
            fiber.complete = function () {
                host.replaceChildren();
                fiberComplete.call(this);
            };
        });
    },

    destroy() {
        // Ensure a reference to editableDescendants
        const editableDescendants = this.getEditableDescendants?.(this.el) || {};
        // Ensure child widgets are destroyed properly before this.
        this._super();
        // Destroy OWL Objects
        this.componentRoot?.destroy();
        // Ensure editableDescendants are preserved in the DOM
        this.el.append(...Object.values(editableDescendants));
    },

    getComponentInfo({ Component: ComponentClass, getEditableDescendants, getProps, name }) {
        const WithSubEnv = class extends ComponentClass {
            static props = {
                ...ComponentClass.props,
                subEnv: Object,
            };

            setup() {
                useSubEnv(this.props.subEnv);
                super.setup();
            }
        };
        const subEnv = {};
        if (getEditableDescendants) {
            this.getEditableDescendants = getEditableDescendants;
            subEnv.getEditableDescendants = getEditableDescendants;
        }
        const props = {
            ...(getProps?.(this.el) || {}),
            subEnv,
        };
        this.setupNewComponent({ name: name, env: subEnv, props });
        return [WithSubEnv, props];
    },

    getEmbedding(name) {
        return getEmbeddingMap(KNOWLEDGE_PUBLIC_EMBEDDINGS).get(name);
    },

    setupNewComponent({ name, env, props }) {
        if (name === "tableOfContent") {
            Object.assign(props, {
                // Define the TOC scope to its siblings.
                manager: getTocManager(this.el.parentElement),
            });
        } else if (name === "view") {
            const resId = this.el.closest(".o_knowledge_public_view")?.dataset.res_id;
            Object.assign(env, { articleId: resId ? parseInt(resId) : undefined });
        }
    },
});

publicWidget.registry.EmbeddedComponentPublicWidget = EmbeddedComponentPublicWidget;
