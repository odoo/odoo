/** @odoo-module native */
import { Component, onMounted, onWillDestroy, useRef, useSubEnv } from "@odoo/owl";
import { uniqueId } from "@web/core/utils/functions";
import { useChildRef, useSpellCheck } from "@web/core/utils/hooks";

import { Editor } from "./editor.js";
import { LocalOverlayContainer } from "./local_overlay_container.js";
import { Toolbar } from "./main/toolbar/toolbar.js";

/**
 * @typedef { import("./editor").EditorConfig } EditorConfig
 */

function copyCssRules(sourceDoc, targetDoc) {
    for (const sheet of sourceDoc.styleSheets) {
        const rules = [];
        for (const r of sheet.cssRules) {
            rules.push(r.cssText);
        }
        const cssRules = rules.join(" ");
        const styleTag = targetDoc.createElement("style");
        styleTag.appendChild(targetDoc.createTextNode(cssRules));
        targetDoc.head.appendChild(styleTag);
    }
}

export class Wysiwyg extends Component {
    static template = "html_editor.Wysiwyg";
    static components = { Toolbar, LocalOverlayContainer };
    static props = {
        config: { type: Object, optional: true },
        class: { type: String, optional: true },
        contentClass: { type: String, optional: true },
        style: { type: String, optional: true },
        iframe: { type: Boolean, optional: true },
        copyCss: { type: Boolean, optional: true },
        onLoad: { type: Function, optional: true },
        onAttached: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true },
    };

    static defaultProps = {
        onLoad: () => {},
        onAttached: () => {},
        onBlur: () => {},
    };

    setup() {
        this.overlayRef = useChildRef();
        useSubEnv({
            localOverlayContainerKey: uniqueId("wysiwyg"),
        });
        const contentRef = useRef("content");
        this.editor = this.props.editor;
        const config = this.getEditorConfig();
        this.editor = new Editor(config, this.env.services);
        this.props.onLoad(this.editor);
        useSpellCheck({
            refName: "content",
        });

        onMounted(() => {
            /** @type { any } */
            const el = contentRef.el;

            if (el.tagName === "IFRAME") {
                const attachEditor = () => {
                    if (!this.editor.isDestroyed) {
                        if (this.props.copyCss) {
                            copyCssRules(document, el.contentDocument);
                        }
                        const additionalClasses = el.dataset.class?.trim().split(" ");
                        if (additionalClasses) {
                            for (const c of additionalClasses) {
                                el.contentDocument.body.classList.add(c);
                            }
                        }
                        this.editor.attachTo(el.contentDocument.body);
                        this.props.onAttached(this.editor);
                    }
                };
                if (el.contentDocument.readyState === "complete") {
                    attachEditor();
                } else {
                    el.addEventListener("load", attachEditor, { once: true });
                }
            } else {
                this.editor.attachTo(el);
                this.props.onAttached(this.editor);
            }
        });
        onWillDestroy(() => this.editor.destroy(true));
    }

    getEditorConfig() {
        return {
            ...this.props.config,
            localOverlayContainers: {
                key: this.env.localOverlayContainerKey,
                ref: this.overlayRef,
            },
        };
    }
}
