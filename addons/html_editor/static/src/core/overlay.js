import { Component, useEffect, useExternalListener, useRef, xml } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";

export class EditorOverlay extends Component {
    static template = xml`
        <div t-ref="root" class="overlay position-absolute">
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
            getTarget = this.getCurrentRect.bind(this);
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

        position = usePosition("root", getTarget, this.props.config);
    }

    getCurrentRect() {
        const doc = this.props.editable.ownerDocument;
        const selection = doc.getSelection();
        if (!selection || !selection.rangeCount) {
            return null;
        }
        const inEditable = this.props.editable.contains(selection.anchorNode);
        let range, focusNode;
        if (inEditable) {
            range = selection.getRangeAt(0);
            focusNode = selection.focusNode;
        } else {
            if (!this.lastSelection) {
                return null;
            }
            range = this.lastSelection.range;
            focusNode = this.lastSelection.focusNode;
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
        this.lastSelection = {
            range,
            focusNode,
        };
        // not proud of this...
        if (focusNode.nodeType === Node.TEXT_NODE) {
            focusNode.getBoundingClientRect = () => rect;
        }
        return focusNode;
    }
}
