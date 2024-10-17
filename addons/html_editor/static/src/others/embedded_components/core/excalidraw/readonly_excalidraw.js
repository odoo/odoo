import { isMobileOS } from "@web/core/browser/feature_detection";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { checkURL, excalidrawWebsiteDomainList } from "@html_editor/utils/url";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { useMouseResizeListeners } from "@html_editor/others/embedded_components/core/excalidraw/excalidraw_utils";

/**
 * This Behavior loads an Excalidraw iframe to grant users the ability to present schematics and
 * slides.
 */
export class ReadonlyEmbeddedExcalidrawComponent extends Component {
    static template = "html_editor.ReadonlyEmbeddedExcalidraw";
    static props = {
        height: { type: String, optional: true },
        host: { type: Object },
        source: { type: String },
        width: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.isMobile = isMobileOS();
        this.state = useState({
            height: this.props.height || "400px",
            source: this.props.source,
            width: this.isMobile ? "100%" : this.props.width || "100%",
        });
        this.displayState = useState({
            hasError: false,
            isResizing: false,
        });
        this.drawContainer = useRef("drawContainer");

        onWillStart(() => this.setupIframe());

        this.onHandleMouseDown = useMouseResizeListeners({
            document: this.props.host.ownerDocument,
            onMouseDown: this.onMouseDown,
            onMouseMove: this.onMouseMove,
            onMouseUp: this.onMouseUp,
        });
    }

    get templateState() {
        return this.state;
    }

    setupIframe() {
        const url = checkURL(this.props.source, excalidrawWebsiteDomainList);
        if (url) {
            this.setURL(url);
        } else {
            this.displayState.hasError = true;
        }
    }

    setURL(url) {
        this.state.source = url;
    }

    onMouseDown() {
        if (!this.drawContainer.el) {
            return;
        }
        this.displayState.isResizing = true;
        const bounds = this.drawContainer.el.getBoundingClientRect();
        let offsetY = 0;
        let offsetX = 0;
        let frameElement = this.drawContainer.el.ownerDocument.defaultView.frameElement;
        while (frameElement) {
            offsetY += frameElement.getBoundingClientRect().top;
            offsetX += frameElement.getBoundingClientRect().left;
            frameElement = frameElement.ownerDocument.defaultView.frameElement;
        }
        this.refPoint = {
            x: bounds.x + bounds.width / 2,
            y: bounds.y,
            offsetY,
            offsetX,
        };
    }

    onMouseMove(event) {
        event.preventDefault();
        this.state.width = this.isMobile
            ? this.state.width
            : `${Math.round(
                  Math.max(
                      2 * Math.abs(this.refPoint.x - event.clientX - this.refPoint.offsetX),
                      300
                  )
              )}px`;
        this.state.height = `${Math.round(
            Math.max(event.clientY - this.refPoint.offsetY - this.refPoint.y, 300)
        )}px`;
    }

    onMouseUp() {
        this.displayState.isResizing = false;
    }
}

export const readonlyExcalidrawEmbedding = {
    name: "draw",
    Component: ReadonlyEmbeddedExcalidrawComponent,
    getProps: (host) => {
        return { ...getEmbeddedProps(host), host };
    },
};
