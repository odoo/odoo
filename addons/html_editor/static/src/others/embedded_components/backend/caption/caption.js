import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { Component, useState, useRef, onMounted, onWillDestroy } from "@odoo/owl";

export class EmbeddedCaptionComponent extends Component {
    static template = "html_editor.EmbeddedCaption";

    static props = {
        image: { type: Element },
        onUpdateCaption: { type: Function },
        onEditorHistoryApply: { type: Function },
        focusInput: { type: Boolean },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.state = useState({
            caption: "",
            host: this.props.host,
        });
        this.captionInput = useRef("captionInput");
        if (this.props.focusInput) {
            onMounted(() => {
                this.captionInput.el.focus();
            });
        }
        // Ensure the state, the attribute and the placeholder are in sync.
        this.updateCaption();
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === "attributes" && mutation.attributeName === "data-caption") {
                    this.updateCaption();
                }
            }
        });
        observer.observe(this.props.image, { attributes: true });
        onWillDestroy(() => {
            observer.disconnect();
        });
    }

    updateCaption(caption = this.props.image.getAttribute("data-caption")) {
        if (caption !== this.state.caption) {
            this.state.caption = caption;
            this.props.onUpdateCaption(caption);
        }
    }

    onInputBlur() {
        // This is triggered before the selection changes. Wait before updating
        // so when the history step triggers a normalization, it restores that
        // new selection and not the old one.
        setTimeout(() => {
            if (this.captionInput.el) {
                this.updateCaption(this.captionInput.el.value || "");
            }
        });
    }

    onInputKeyup(ev) {
        if (ev.key === "z" && ev.ctrlKey && !this._appliedNativeHistory) {
            this.props.onEditorHistoryApply(ev.shiftKey);
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
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    caption: (state, previous, next) => {
                        applyObjectPropertyDifference(
                            state,
                            "caption",
                            previous.caption,
                            next.caption
                        );
                    },
                },
            })
        ),
};
