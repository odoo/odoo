import { Component, onWillDestroy, useEffect, useExternalListener, useRef, xml } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";
import { useActiveElement } from "@web/core/ui/ui_service";
import { omit } from "@web/core/utils/objects";

export class EditorOverlay extends Component {
    static template = xml`
        <div t-ref="root" class="overlay">
            <t t-component="props.Component" t-props="props.props"/>
        </div>`;

    static props = {
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE, optional: true },
        initialSelection: { type: Object, optional: true },
        config: Object,
        Component: Function,
        props: { type: Object, optional: true },
        editable: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        bus: Object,
        getContainer: Function,
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

        if (this.props.config.hasAutofocus) {
            useActiveElement("root");
        }
        const positionConfig = {
            position: "bottom-start",
            container: this.props.getContainer,
            ...omit(this.props.config, "hasAutofocus", "onPositioned"),
            onPositioned: (el, solution) => {
                this.props.config.onPositioned?.(el, solution);
                this.updateVisibility(el, solution);
            },
        };
        position = usePosition("root", getTarget, positionConfig);
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
            const clonedRange = range.cloneRange();
            const shadowCaret = doc.createTextNode("|");
            clonedRange.insertNode(shadowCaret);
            clonedRange.selectNode(shadowCaret);
            rect = clonedRange.getBoundingClientRect();
            shadowCaret.remove();
            clonedRange.detach();
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
