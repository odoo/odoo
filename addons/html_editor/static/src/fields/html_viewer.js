import {
    App,
    Component,
    onMounted,
    onWillStart,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { getBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";

// Ensure all links are opened in a new tab.
function retargetLinks(container) {
    for (const link of container.querySelectorAll("a")) {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noreferrer");
    }
}

export class HtmlViewer extends Component {
    static template = "html_editor.HtmlViewer";
    static props = {
        config: { type: Object },
    };
    static defaultProps = {
        hasFullHtml: false,
    };

    setup() {
        this.iframeRef = useRef("iframe");

        this.state = useState({
            iframeVisible: false,
        });

        if (this.showIframe) {
            onMounted(() => {
                const onLoadIframe = () => this.onLoadIframe(this.props.config.value);
                this.iframeRef.el.addEventListener("load", onLoadIframe, { once: true });
                // Force the iframe to call the `load` event. Without this line, the
                // event 'load' might never trigger.
                this.iframeRef.el.after(this.iframeRef.el);
            });

            onWillUpdateProps((nextProps) => {
                this.updateIframeContent(nextProps.config.value);
            });
        } else {
            this.readonlyElementRef = useRef("readonlyContent");
            useEffect(() => {
                retargetLinks(this.readonlyElementRef.el);
            });
        }

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
            this.components = new Set();
            useEffect(
                () => {
                    if (this.readonlyElementRef?.el) {
                        this.mountComponents();
                    }
                    return () => this.destroyComponents();
                },
                () => [this.props.config.value, this.readonlyElementRef?.el]
            );
        }
    }

    get showIframe() {
        return this.props.config.hasFullHtml || this.props.config.cssAssetId;
    }

    updateIframeContent(content) {
        const contentWindow = this.iframeRef.el.contentWindow;
        const iframeTarget = this.props.config.hasFullHtml
            ? contentWindow.document.documentElement
            : contentWindow.document.querySelector("#iframe_target");
        iframeTarget.innerHTML = content;
        retargetLinks(iframeTarget);
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

        this.updateIframeContent(this.props.config.value);
        this.state.iframeVisible = true;
    }

    //--------------------------------------------------------------------------
    // Embedded Components
    //--------------------------------------------------------------------------

    destroyComponent({ app, host }) {
        const { getEditableDescendants } = this.getEmbedding(host);
        const editableDescendants = getEditableDescendants?.(host) || {};
        app.destroy();
        this.components.delete(arguments[0]);
        host.append(...Object.values(editableDescendants));
    }

    destroyComponents() {
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

    mountComponent(host, { Component, getEditableDescendants, getProps }) {
        const props = getProps?.(host) || {};
        const mainApp = this.__owl__.app;
        const { dev, translateFn, getRawTemplate } = mainApp;
        // TODO ABD TODO @phoenix: check if there is too much info in the htmlViewer env.
        // i.e.: env has X because of parent component,
        // embedded component descendant sometimes uses X from env which is set conditionally:
        // -> it will override the one one from the parent => OK.
        // -> it will not => the embedded component still has X in env because of its ancestors => Issue.
        const env = Object.create(this.env);
        if (getEditableDescendants) {
            env.getEditableDescendants = getEditableDescendants;
        }
        const app = new App(Component, {
            test: dev,
            env,
            translateFn,
            getTemplate: getRawTemplate,
            props,
        });
        // copy templates so they don't have to be recompiled.
        app.rawTemplates = mainApp.rawTemplates;
        app.templates = mainApp.templates;
        app.mount(host);
        // Patch mount fiber to hook into the exact call stack where app is
        // mounted (but before). This will remove host children synchronously
        // just before adding the app rendered html.
        const fiber = Array.from(app.scheduler.tasks)[0];
        const fiberComplete = fiber.complete;
        fiber.complete = function () {
            host.replaceChildren();
            fiberComplete.call(this);
        };
        const info = {
            app,
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
