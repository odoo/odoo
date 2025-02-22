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
    static selector = "[data-embedded]";

    dynamicContent = {
        _root: {
            "t-component": () => this.getComponentInfo(),
        },
    };

    static getEmbeddings() {
        return PUBLIC_EMBEDDINGS;
    }

    static getEmbeddingMap = memoize(
        (embeddings) => new Map(embeddings.map((embedding) => [embedding.name, embedding]))
    );

    static getTocManager = memoize(
        (element) =>
            new TableOfContentManager({
                el: element,
            })
    );

    destroy() {
        // TODO: test this, interaction_service first destroys every interaction,
        // then it destroys OWL roots. Meaning the DOM manipulation will be done on
        // live OWL components which will then be destroyed, should work but better be sure.
        this.el.append(...Object.values(this.getEditableDescendants?.(this.el) || {}));
    }

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
            this.getEditableDescendants = getEditableDescendants;
            subEnv.getEditableDescendants = getEditableDescendants;
        }
        const props = {
            ...(getProps?.(this.el) || {}),
            subEnv,
        };
        this.setupNewComponent({ name: name, env: subEnv, props });
        return [Extended, props];
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
