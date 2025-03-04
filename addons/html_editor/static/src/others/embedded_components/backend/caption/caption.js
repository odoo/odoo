import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { Component, useEffect, useState, useRef, onMounted } from "@odoo/owl";

export class EmbeddedCaptionComponent extends Component {
    static template = "html_editor.EmbeddedCaption";

    static props = {
        id: { type: String },
        editable: { type: Element },
        addHistoryStep: { type: Function },
        undo: { type: Function },
        redo: { type: Function },
        focusInput: { type: Boolean },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.image = this.props.editable.querySelector(`img[data-caption-id="${this.props.id}"]`);
        this.state = useState({
            caption: this.image.getAttribute("data-caption") || "",
            host: this.props.host,
        });
        this.captionInput = useRef("captionInput");
        if (this.props.focusInput) {
            onMounted(() => {
                this.captionInput.el.focus();
            })
        }
        useEffect(() => {
            this.image.setAttribute("data-caption", this.state.caption);
            // Adapt the figcaption element's placeholder to the new caption
            // for screen reader users.
            this.captionInput.el.parentElement.setAttribute("placeholder", this.state.caption);
            this.props.addHistoryStep();
        }, () => [this.state.caption]);
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

    onInputBlur() {
        this.state.caption = this.captionInput.el.value;
    }

    onInputKeyup(ev) {
        if (ev.key === "z" && ev.ctrlKey && !this._appliedNativeHistory) {
            if (ev.shiftKey) {
                this.props.redo();
            } else {
                this.props.undo();
            }
        }
        this._appliedNativeHistory = false;
    }

    onInputBeforeInput(ev) {
        this._appliedNativeHistory = false;
        if (ev.inputType === "historyUndo" || ev.inputType === "historyRedo") {
            // Input elements handle their own history, but this event is not
            // triggered if no changes were made to the input. So we handle the
            // editor history on keyup in those cases, but let the browser do
            // its thing otherwise.
            this._appliedNativeHistory = true;
        }
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
