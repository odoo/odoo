import { render, useRef, useSubEnv } from "@web/owl2/utils";
import { Component, onMounted, onWillDestroy, props, t } from "@odoo/owl";
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

export const wysiwygProps = {
    config: t.object().optional(),
    class: t.string().optional(),
    contentClass: t.string().optional(), // on editable element
    style: t.string().optional(),
    iframe: t.boolean().optional(),
    copyCss: t.boolean().optional(),
    onLoad: t.function().optional(() => () => {}),
    onBlur: t.function().optional(() => () => {}),
    dynamicPlaceholder: t.boolean().optional(),
};

export class Wysiwyg extends Component {
    static template = "html_editor.Wysiwyg";
    static components = { Toolbar, LocalOverlayContainer };
    props = props(wysiwygProps);

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
                            render(this);
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
            localOverlayContainers: {
                key: this.env.localOverlayContainerKey,
                ref: this.overlayRef,
            },
        };
    }
}
