import { Component, onMounted, onWillDestroy, useRef, useState, useSubEnv } from "@odoo/owl";
import { Editor } from "./editor";
import { Toolbar } from "./main/toolbar/toolbar";
import { useChildRef, useSpellCheck } from "@web/core/utils/hooks";
import { LocalOverlayContainer } from "./local_overlay_container";
import { uniqueId } from "@web/core/utils/functions";

/**
 * @typedef { import("./editor").EditorConfig } EditorConfig
 **/

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
        contentClass: { type: String, optional: true }, // on editable element
        style: { type: String, optional: true },
        toolbar: { type: Boolean, optional: true },
        iframe: { type: Boolean, optional: true },
        copyCss: { type: Boolean, optional: true },
        onLoad: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true },
    };

    static defaultProps = {
        onLoad: () => {},
        onBlur: () => {},
    };

    setup() {
        this.state = useState({
            showToolbar: false,
        });
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
            // now that component is mounted, editor is attached to el, and
            // plugins are started, so we can allow the toolbar to be displayed
            this.state.showToolbar = true;
            /** @type { any } **/
            const el = contentRef.el;

            if (el.tagName === "IFRAME") {
                // grab the inner body instead
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
                    }
                };
                if (el.contentDocument.readyState === "complete") {
                    attachEditor();
                } else {
                    // in firefox, iframe is not immediately available. we need to wait
                    // for it to be ready before mounting editor
                    el.addEventListener(
                        "load",
                        () => {
                            attachEditor();
                            this.render();
                        },
                        { once: true }
                    );
                }
            } else {
                this.editor.attachTo(el);
            }
        });
        onWillDestroy(() => this.editor.destroy(true));
    }

    getEditorConfig() {
        return {
            ...this.props.config,
            // TODO ABD TODO @phoenix: check if there is too much info in the wysiwyg env.
            // i.e.: env has X because of parent component,
            // embedded component descendant sometimes uses X from env which is set conditionally:
            // -> it will override the one one from the parent => OK.
            // -> it will not => the embedded component still has X in env because of its ancestors => Issue.
            embeddedComponentInfo: { app: this.__owl__.app, env: this.env },
            localOverlayContainers: {
                key: this.env.localOverlayContainerKey,
                ref: this.overlayRef,
            },
            disableFloatingToolbar: this.props.toolbar,
        };
    }
}
