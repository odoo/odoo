import { closestBlock } from "@html_editor/utils/blocks";
import { Component, useEffect, useExternalListener, useRef, useState, xml } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";
import { useActiveElement } from "@web/core/ui/ui_service";
import { omit } from "@web/core/utils/objects";

export class EditorOverlay extends Component {
    static template = xml`
        <div t-ref="root" class="overlay">
            <t t-if="state.display" t-component="props.Component" t-props="props.props"/>
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

        this.state = useState({
            display: true,
        });
        if (this.props.target) {
            getTarget = () => {
                const target = this.props.target;
                this.updateVisibility(target.getBoundingClientRect(), target);
                return target;
            };
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

        if (this.props.config.hasAutofocus) {
            useActiveElement("root");
        }
        const positionConfig = {
            position: "bottom-start",
            ...omit(this.props.config, "hasAutofocus"),
        };
        position = usePosition("root", getTarget, positionConfig);
    }

    updateVisibility(rect, focusNode) {
        const centerX = rect.left + rect.width / 2;
        const topY = rect.top + 1;

        const document = this.props.editable.ownerDocument;
        const visibleElTop = document.elementFromPoint(centerX, topY);

        const target = closestBlock(focusNode);

        if (!visibleElTop) {
            this.state.display = false;
            return;
        }

        const topIsOverlay = visibleElTop.closest(".overlay");
        if (topIsOverlay) {
            const { bottom } = topIsOverlay.getBoundingClientRect();
            const el = document.elementFromPoint(centerX, bottom + 1);
            this.state.display = this.props.editable.contains(el);
            return;
        }

        const targetIsVisible = target.contains(visibleElTop);
        this.state.display = targetIsVisible;
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
        this.updateVisibility(rect, focusNode);
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
