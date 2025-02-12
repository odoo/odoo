import { registry } from "@web/core/registry";
import { Component, useSubEnv, xml } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { PUBLIC_EMBEDDINGS } from "@html_editor/public/embedding_sets";
import { memoize } from "@web/core/utils/functions";
import { TableOfContentManager } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";

class EmbeddedDummy extends Component {
    static template = xml``;
    static props = {};
}

export class EmbeddedComponentInteraction extends Interaction {
    static getTocManager = memoize(
        (element) =>
            new TableOfContentManager({
                el: element,
            })
    );
    static selector = "[data-embedded]";
    static getEmbeddingMap = memoize(
        (embeddings) => new Map(embeddings.map((embedding) => [embedding.name, embedding]))
    );
    static getEmbeddings() {
        return PUBLIC_EMBEDDINGS;
    }
    dynamicContent = {
        _root: {
            "t-component": () => this.getComponentInfo(),
        },
    };

    getComponentInfo() {
        const {
            Component: C,
            getEditableDescendants,
            getProps,
            name,
        } = EmbeddedComponentInteraction.getEmbeddingMap(
            EmbeddedComponentInteraction.getEmbeddings()
        ).get(this.el.dataset.embedded) ?? { C: EmbeddedDummy };
        const Extended = class extends C {
            static props = {
                ...C.props,
                subEnv: Object,
            };

            setup() {
                useSubEnv(this.props.subEnv);
                super.setup();
            }
        };
        const subEnv = {};
        if (getEditableDescendants) {
            subEnv.getEditableDescendants = () => getEditableDescendants(this.el);
        }
        const props = {
            ...(getProps?.(this.el) || {}),
            subEnv,
        };
        this.setupNewComponent({ name: name, env: subEnv, props });
        return [Extended, props];
    }

    getEmbedding(host) {
        return this.embeddingMap.get(host.dataset.embedded);
    }

    setupNewComponent({ name, env, props }) {
        if (name === "tableOfContent") {
            Object.assign(props, {
                // Define the TOC scope to its siblings.
                manager: EmbeddedComponentInteraction.getTocManager(this.el.parentElement),
            });
        }
    }
}

registry
    .category("public.interactions")
    .add("html_editor.embedded_component", EmbeddedComponentInteraction);
