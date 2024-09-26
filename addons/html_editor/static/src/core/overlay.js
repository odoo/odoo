import { Component, onWillDestroy, useEffect, useExternalListener, useRef, xml } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";
import { useActiveElement } from "@web/core/ui/ui_service";

export class EditorOverlay extends Component {
    static template = xml`
        <div t-ref="root" class="overlay" t-att-class="props.className" t-on-pointerdown.stop="() => {}">
            <t t-component="props.Component" t-props="props.props"/>
        </div>`;

    static props = {
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE, optional: true },
        initialSelection: { type: Object, optional: true },
        Component: Function,
        props: { type: Object, optional: true },
        editable: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        bus: Object,
        getContainer: Function,
        history: Object,
        close: Function,

        // Props from createOverlay
        positionOptions: { type: Object, optional: true },
        className: { type: String, optional: true },
        closeOnPointerdown: { type: Boolean, optional: true },
        hasAutofocus: { type: Boolean, optional: true },
    };

    static defaultProps = {
        className: "",
        closeOnPointerdown: true,
        hasAutofocus: false,
    };

    setup() {
        this.lastSelection = this.props.initialSelection;
        let getTarget, position;
        if (this.props.target) {
            getTarget = () => this.props.target;
        } else {
            useExternalListener(this.props.bus, "updatePosition", () => {
                position.unlock();
            });
            const editable = this.props.editable;
            this.rangeElement = editable.ownerDocument.createElement("range-el");
            editable.after(this.rangeElement);
            onWillDestroy(() => {
                this.rangeElement.remove();
            });
            getTarget = this.getSelectionTarget.bind(this);
        }

        const rootRef = useRef("root");
        const resizeObserver = new ResizeObserver(() => {
            position.unlock();
        });
        useEffect(
            (root) => {
                resizeObserver.observe(root);
                return () => {
                    resizeObserver.unobserve(root);
                };
            },
            () => [rootRef.el]
        );

        if (this.props.closeOnPointerdown) {
            const editableDocument = this.props.editable.ownerDocument;
            useExternalListener(editableDocument, "pointerdown", this.props.close);
            // Listen to pointerdown outside the iframe
            if (editableDocument !== document) {
                useExternalListener(document, "pointerdown", this.props.close);
            }
        }

        if (this.props.hasAutofocus) {
            useActiveElement("root");
        }
        const positionOptions = {
            position: "bottom-start",
            container: this.props.getContainer,
            ...this.props.positionOptions,
            onPositioned: (el, solution) => {
                this.props.positionOptions?.onPositioned?.(el, solution);
                this.updateVisibility(el, solution);
            },
        };
        position = usePosition("root", getTarget, positionOptions);
    }

    getSelectionTarget() {
        const doc = this.props.editable.ownerDocument;
        const selection = doc.getSelection();
        if (!selection || !selection.rangeCount) {
            return null;
        }
        const inEditable = this.props.editable.contains(selection.anchorNode);
        let range;
        if (inEditable) {
            range = selection.getRangeAt(0);
            this.lastSelection = { range };
        } else {
            if (!this.lastSelection) {
                return null;
            }
            range = this.lastSelection.range;
        }
        let rect = range.getBoundingClientRect();
        if (rect.x === 0 && rect.width === 0 && rect.height === 0) {
            // Attention, using disableObserver and enableObserver is always dangerous (when we add or remove nodes)
            // because if another mutation uses the target that is not observed, that mutation can never be applied
            // again (when undo/redo and in collaboration).
            this.props.history.disableObserver();
            const clonedRange = range.cloneRange();
            const shadowCaret = doc.createTextNode("|");
            clonedRange.insertNode(shadowCaret);
            clonedRange.selectNode(shadowCaret);
            rect = clonedRange.getBoundingClientRect();
            shadowCaret.remove();
            clonedRange.detach();
            this.props.history.enableObserver();
        }
        // Html element with a patched getBoundingClientRect method. It
        // represents the range as a (HTMLElement) target for the usePosition
        // hook.
        this.rangeElement.getBoundingClientRect = () => rect;
        return this.rangeElement;
    }

    updateVisibility(overlayElement, solution) {
        // @todo: mobile tests rely on a visible (yet overflowing) toolbar
        // Remove this once the mobile toolbar is fixed?
        if (this.env.isSmall) {
            return;
        }
        const containerRect = this.props.getContainer().getBoundingClientRect();
        overlayElement.style.visibility = solution.top > containerRect.top ? "visible" : "hidden";
    }
}
