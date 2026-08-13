import { Component, onMounted, onWillDestroy, signal, t, useProps } from "@odoo/owl";
import { uniqueId } from "@web/core/utils/functions";
import { useSpellCheck } from "@web/core/utils/hooks";
import { render } from "@web/owl2/utils";
import { useEditor } from "./editor";
import { LocalOverlayContainer } from "./local_overlay_container";
import { Toolbar } from "./main/toolbar/toolbar";

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
    props = useProps(wysiwygProps);

    contentRef = signal.ref();

    setup() {
        this.overlayRef = signal.ref();
        this.localOverlayContainerKey = uniqueId("wysiwyg");
        this.editor = this.props.editor;
        const config = this.getEditorConfig();
        this.editor = useEditor(config);
        this.props.onLoad(this.editor);
        useSpellCheck({
            ref: this.contentRef,
        });

        onMounted(() => {
            /** @type { any } **/
            const el = this.contentRef();

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
                key: this.localOverlayContainerKey,
                ref: this.overlayRef,
            },
        };
    }
}
