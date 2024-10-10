import { Component, onWillDestroy, useRef, useState } from "@odoo/owl";

export class BuilderOverlay extends Component {
    static template = "mysterious_egg.BuilderOverlay";
    setup() {
        this.overlay = useRef("overlay");
        this.size = useState({
            height: this.props.target.clientHeight,
            width: this.props.target.clientWidth,
        });
        // TODO: we can use the editor overlay service instead
        // But to do so we have to modify computePosition to
        // add the "full" direction
        this.position = this.getOffset(this.props.target);
    }

    getOffset(target) {
        if (!target.getClientRects().length) {
            return { top: 0, left: 0 };
        } else {
            const rect = target.getBoundingClientRect();
            const win = target.ownerDocument.defaultView;
            const frameElement = target.ownerDocument.defaultView.frameElement;
            const offset = { top: 0, left: 0 };
            if (frameElement) {
                const frameRect = frameElement.getBoundingClientRect();
                offset.left += frameRect.left;
                offset.top += frameRect.top;
            }
            return {
                top: rect.top + win.pageYOffset + offset.top,
                left: rect.left + win.pageXOffset + offset.left,
            };
        }
    }
}
