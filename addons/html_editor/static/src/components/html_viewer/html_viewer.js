import {
    Component,
    markup,
    onMounted,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { getBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";
import { fillHtmlTransferData } from "@html_editor/utils/clipboard";
import { fixInvalidHTML, instanceofMarkup } from "@html_editor/utils/sanitize";
import { HtmlUpgradeManager } from "@html_editor/html_migrations/html_upgrade_manager";
import { TableOfContentManager } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";
import { scrollAndHighlightHeading } from "@html_editor/utils/url";

export class HtmlViewer extends Component {
    static template = "html_editor.HtmlViewer";
    static props = {
        config: { type: Object },
        migrateHTML: { type: Boolean, optional: true },
    };
    static defaultProps = {
        migrateHTML: true,
    };

    setup() {
        this._cleanups = [];
        this.htmlUpgradeManager = new HtmlUpgradeManager();
        this.iframeRef = useRef("iframe");

        this.state = useState({
            iframeVisible: false,
            value: this.formatValue(this.props.config.value),
        });
        this.components = new Set();

        onWillUpdateProps((newProps) => {
            const newValue = this.formatValue(newProps.config.value);
            if (newValue.toString() !== this.state.value.toString()) {
                this.state.value = this.formatValue(newProps.config.value);
                if (this.props.config.embeddedComponents) {
                    this.destroyComponents();
                }
                if (this.showIframe) {
                    this.updateIframeContent(this.state.value);
                }
            }
        });

        onWillUnmount(() => {
            this.destroyComponents();
        });

        if (this.showIframe) {
            onMounted(() => {
                const onLoadIframe = () => this.onLoadIframe(this.state.value);
                this.iframeRef.el.addEventListener("load", onLoadIframe, { once: true });
                // Force the iframe to call the `load` event. Without this line, the
                // event 'load' might never trigger.
                this.iframeRef.el.after(this.iframeRef.el);
            });
        } else {
            this.readonlyElementRef = useRef("readonlyContent");
            useEffect(
                () => {
                    this.processReadonlyContent(this.readonlyElementRef.el);
                },
                () => [this.props.config.value.toString(), this.readonlyElementRef?.el]
            );
        }

        onMounted(() => {
            scrollAndHighlightHeading(this.readonlyElementRef?.el || this.iframeRef?.el);
        });

        if (this.props.config.cssAssetId) {
            onWillStart(async () => {
                this.cssAsset = await getBundle(this.props.config.cssAssetId);
            });
        }

        if (this.props.config.embeddedComponents) {
            // TODO @phoenix: should readonly iframe with embedded components be supported?
            this.embeddedComponents = memoize((embeddedComponents = []) => {
                const result = {};
                for (const embedding of embeddedComponents) {
                    result[embedding.name] = embedding;
                }
                return result;
            });
            useEffect(
                () => {
                    if (this.readonlyElementRef?.el) {
                        this.mountComponents();
                    }
                },
                () => [this.props.config.value.toString(), this.readonlyElementRef?.el]
            );
            this.tocManager = new TableOfContentManager(this.readonlyElementRef);
        }
    }

    addDomListener(target, eventName, fn, capture = false) {
        const handler = (ev) => {
            fn?.call(this, ev);
        };
        target.addEventListener(eventName, handler, capture);
        this._cleanups.push(() => target.removeEventListener(eventName, handler, capture));
    }

    get showIframe() {
        return this.props.config.hasFullHtml || this.props.config.cssAssetId;
    }

    /**
     * Allows overrides to process the value used in the Html Viewer.
     * Typically, if the value comes from the html_field, it is already fixed
     * (invalid and obsolete elements were replaced). If used as a standalone,
     * the HtmlViewer has to handle invalid nodes and html upgrades.
     *
     * @param { string | Markup } value
     * @returns { string | Markup }
     */
    formatValue(value) {
        let newVal = fixInvalidHTML(value);
        if (this.props.migrateHTML) {
            newVal = this.htmlUpgradeManager.processForUpgrade(newVal, {
                containsComplexHTML: this.props.config.hasFullHtml,
                env: this.env,
            });
        }
        if (instanceofMarkup(value)) {
            return markup(newVal);
        }
        return newVal;
    }

    processReadonlyContent(container) {
        this.retargetLinks(container);
        this.applyAccessibilityAttributes(container);
        this.addDomListener(container, "copy", this.onCopy);
    }

    /**
     * @param {ClipboardEvent} ev
     */
    onCopy(ev) {
        ev.preventDefault();
        const selection = ev.target.ownerDocument.defaultView.getSelection();
        const clonedContents = selection.getRangeAt(0).cloneContents();
        fillHtmlTransferData(ev, "clipboardData", clonedContents, {
            textContent: selection.toString(),
        });
    }

    /**
     * Ensure that elements with accessibility editor attributes correctly get
     * the standard accessibility attribute (aria-label, role).
     */
    applyAccessibilityAttributes(container) {
        for (const el of container.querySelectorAll("[data-oe-role]")) {
            el.setAttribute("role", el.dataset.oeRole);
        }
        for (const el of container.querySelectorAll("[data-oe-aria-label]")) {
            el.setAttribute("aria-label", el.dataset.oeAriaLabel);
        }
    }

    /**
     * Ensure all links are opened in a new tab.
     */
    retargetLinks(container) {
        for (const link of container.querySelectorAll("a")) {
            this.retargetLink(link);
        }
    }

    retargetLink(link) {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noreferrer");
    }

    updateIframeContent(content) {
        const contentWindow = this.iframeRef.el.contentWindow;
        const iframeTarget = this.props.config.hasFullHtml
            ? contentWindow.document.documentElement
            : contentWindow.document.querySelector("#iframe_target");
        iframeTarget.innerHTML = content;
        this.processReadonlyContent(iframeTarget);
    }

    onLoadIframe(value) {
        const contentWindow = this.iframeRef.el.contentWindow;
        if (!this.props.config.hasFullHtml) {
            contentWindow.document.open("text/html", "replace").write(
                `<!DOCTYPE html><html>
                        <head>
                            <meta charset="utf-8"/>
                            <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
                            <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>
                        </head>
                        <body class="o_in_iframe o_readonly" style="overflow: hidden;">
                            <div id="iframe_target"></div>
                        </body>
                    </html>`
            );
        }

        if (this.cssAsset) {
            for (const cssLib of this.cssAsset.cssLibs) {
                const link = contentWindow.document.createElement("link");
                link.setAttribute("type", "text/css");
                link.setAttribute("rel", "stylesheet");
                link.setAttribute("href", cssLib);
                contentWindow.document.head.append(link);
            }
        }

        this.updateIframeContent(this.state.value);
        this.state.iframeVisible = true;
    }

    //--------------------------------------------------------------------------
    // Embedded Components
    //--------------------------------------------------------------------------

    destroyComponent({ root, host }) {
        const { getEditableDescendants } = this.getEmbedding(host);
        const editableDescendants = getEditableDescendants?.(host) || {};
        root.destroy();
        this.components.delete(arguments[0]);
        host.append(...Object.values(editableDescendants));
    }

    destroyComponents() {
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        for (const info of [...this.components]) {
            this.destroyComponent(info);
        }
    }

    forEachEmbeddedComponentHost(elem, callback) {
        const selector = `[data-embedded]`;
        const targets = [...elem.querySelectorAll(selector)];
        if (elem.matches(selector)) {
            targets.unshift(elem);
        }
        for (const host of targets) {
            const embedding = this.getEmbedding(host);
            if (!embedding) {
                continue;
            }
            callback(host, embedding);
        }
    }

    getEmbedding(host) {
        return this.embeddedComponents(this.props.config.embeddedComponents)[host.dataset.embedded];
    }

    setupNewComponent({ name, env, props }) {
        if (name === "tableOfContent") {
            Object.assign(props, {
                manager: this.tocManager,
            });
        }
    }

    mountComponent(host, { Component, getEditableDescendants, getProps, name }) {
        const props = getProps?.(host) || {};
        // TODO ABD TODO @phoenix: check if there is too much info in the htmlViewer env.
        // i.e.: env has X because of parent component,
        // embedded component descendant sometimes uses X from env which is set conditionally:
        // -> it will override the one one from the parent => OK.
        // -> it will not => the embedded component still has X in env because of its ancestors => Issue.
        const env = Object.create(this.env);
        if (getEditableDescendants) {
            env.getEditableDescendants = getEditableDescendants;
        }
        this.setupNewComponent({
            name,
            env,
            props,
        });
        const root = this.__owl__.app.createRoot(Component, {
            props,
            env,
        });
        const promise = root.mount(host);
        // Don't show mounting errors as they will happen often when the host
        // is disconnected from the DOM because of a patch
        promise.catch();
        // Patch mount fiber to hook into the exact call stack where root is
        // mounted (but before). This will remove host children synchronously
        // just before adding the root rendered html.
        const fiber = root.node.fiber;
        const fiberComplete = fiber.complete;
        fiber.complete = function () {
            host.replaceChildren();
            fiberComplete.call(this);
        };
        const info = {
            root,
            host,
        };
        this.components.add(info);
    }

    mountComponents() {
        this.forEachEmbeddedComponentHost(this.readonlyElementRef.el, (host, embedding) => {
            this.mountComponent(host, embedding);
        });
    }
}
