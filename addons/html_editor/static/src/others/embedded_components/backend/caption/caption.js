import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { Component, useEffect, useState, useRef } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";

export class EmbeddedCaptionComponent extends Component {
    static template = "html_editor.EmbeddedCaption";

    static props = {
        id: { type: String },
        editable: { type: Element },
        addHistoryStep: { type: Function },
        focusInput: { type: Boolean },
        host: { type: Object },
    };

    setup() {
        super.setup();
        this.image = this.props.editable.querySelector(`img[data-caption-id="${this.props.id}"]`);
        this.state = useState({
            caption: this.image.getAttribute("data-caption") || "",
            isEditing: this.props.focusInput,
            host: this.props.host,
        });
        if (this.props.focusInput) {
            this.captionInput = useAutofocus();
        } else {
            this.captionInput = useRef("autofocus");
        }
        // this.span = useRef("span");
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
        // useEffect(
        //     () => {
        //         if (this.state.isEditing) {
        //             console.log("use effect");
        //             // this.captionInput.el.focus();
        //             // this.captionInput.el.select();
        //             // THE PROBLEM:
        //             // If its parent is not contenteditable, the selection gets
        //             // corrected and the input loses focus immediately.
        //             // If its parent is contenteditable, doing backspace in the
        //             // input triggers the beforeinput event and the input loses
        //             // focus.
        //             // There's a debugger in the blur event of the input.
        //             // Observe the issue by doing backspace in the input and
        //             // checking the call stack of the breakpoint.
        //             // In embedded file, the parent is not contenteditable. How
        //             // come it works anyway?
        //         }
        //     },
        //     () => [this.state.isEditing]
        // );
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
        // this.captionInput.el.focus();
    }

    onSpanFocus() {
        console.log("span focus");
        debugger;
        this.span.el.focus();
        const range = new Range();
        range.selectNodeContents(this.span.el);
        const selection = this.span.el.ownerDocument.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        this.state.isEditing = true;
    }

    onInputCaptionBlur() {
        this.state.isEditing = false;
        debugger;
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
