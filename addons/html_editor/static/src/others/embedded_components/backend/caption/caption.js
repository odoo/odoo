import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { Component, useEffect, useState } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";

export class EmbeddedCaptionComponent extends Component {
    static template = "html_editor.EmbeddedCaption";

    static props = {
        id: { type: String },
        editable: { type: Element },
        addHistoryStep: { type: Function },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.image = this.props.editable.querySelector(`img[data-caption-id="${this.props.id}"]`);
        this.state = useState({
            caption: this.image.getAttribute("data-caption") || "",
            host: this.props.host,
        });
        this.captionInput = useAutofocus();
        useEffect(
            () => {
                this.image.setAttribute("data-caption", this.state.caption);
                // Adapt the figcaption element's placeholder to the new caption
                // for screen reader users.
                this.captionInput.el.parentElement.setAttribute("placeholder", this.state.caption);
                this.props.addHistoryStep();
            },
            () => [this.state.caption]
        );
        // Ensure synchronicity between the state and the attribute.
        this.observer = new MutationObserver(mutations => {
            for (const mutation of mutations) {
                if (mutation.type === "attributes" && mutation.attributeName === "data-caption") {
                    const captionAttribute = this.image.getAttribute("data-caption");
                    if (captionAttribute !== this.state.caption) {
                        this.state.caption = captionAttribute;
                    }
                }
            }
        });
        this.observer.observe(this.image, { attributes: true });
    }

    destroy() {
        this.observer.disconnect();
    }

    onInputCaptionInput() {
        this.state.caption = this.captionInput.el.value;
    }

}

export const captionEmbedding = {
    name: "caption",
    Component: EmbeddedCaptionComponent,
    getProps: (host) => {
        return { host, ...getEmbeddedProps(host) };
    },
    getStateChangeManager: (config) => {
        return new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    caption: (state, previous, next) => {
                        applyObjectPropertyDifference(
                            state,
                            "caption",
                            previous.caption,
                            next.caption,
                        );
                    },
                },
            })
        );
    },
};
