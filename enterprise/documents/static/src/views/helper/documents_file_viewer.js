/* @odoo-module **/

import { FileViewer } from "@documents/attachments/document_file_viewer";
import { Component, useEffect, useRef, useState } from "@odoo/owl";

export class DocumentsFileViewer extends Component {
    static template = "documents.DocumentsFileViewer";
    static components = {
        FileViewer,
    };
    static props = [
        "parentRoot", // Parent's root element, used to know the zone to use.
        "previewStore",
    ];

    setup() {
        this.root = useRef("root");
        this.state = useState({
            topOffset: 0,
            leftOffset: 0,
        });

        const onKeydown = this.onIframeKeydown.bind(this);
        useEffect(
            (iframe) => {
                if (!iframe) {
                    return;
                }
                // We need to wait until the iframe is loaded to be able to bind our keydown handler.
                const onLoad = () => {
                    // In case of youtube links contentDocument might be null.
                    if (!iframe.contentDocument) {
                        return;
                    }
                    iframe.contentDocument.addEventListener("keydown", onKeydown);
                };
                iframe.addEventListener("load", onLoad);
                return () => {
                    iframe.removeEventListener("load", onLoad);
                };
            },
            () => [this.root.el && this.root.el.querySelector("iframe")]
        );
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                this.state.topOffset = el.scrollTop;
                this.state.leftOffset = el.scrollLeft;
                const scrollHandler = () => {
                    this.state.topOffset = el.scrollTop;
                    this.state.leftOffset = el.scrollLeft;
                };
                el.addEventListener("scroll", scrollHandler);
                return () => {
                    el.removeEventListener("scroll", scrollHandler);
                };
            },
            () => [this.parentRoot.el]
        );
    }

    get parentRoot() {
        return this.props.parentRoot;
    }

    onGlobalKeydown(ev) {
        // Some keydown events are not handled by the fileViewer as we want them too
        // making it possible to interact with the background.
        const cancelledKeys = ["ArrowUp", "ArrowDown"];
        if (cancelledKeys.includes(ev.key)) {
            ev.stopPropagation();
        }
    }

    onIframeKeydown(ev) {
        if (ev.key === "Escape") {
            this.env.model.env.documentsView.bus.trigger("documents-close-preview");
        }
    }
}
