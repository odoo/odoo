import {
    Component,
    onMounted,
    onWillStart,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { getBundle } from "@web/core/assets";

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
        value: { type: [Object, String] },
        hasFullHtml: { type: Boolean, optional: true },
        cssAssetId: { type: String, optional: true },
    };
    static defaultProps = {
        hasFullHtml: false,
    };

    setup() {
        this.iframeRef = useRef("iframe");

        this.state = useState({
            iframeVisible: false,
            value: this.formatValue(this.props.value),
        });

        onWillUpdateProps((newProps) => {
            this.state.value = this.formatValue(newProps.value);
            if (this.showIframe) {
                this.updateIframeContent(this.state.value);
            }
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
            useEffect(() => {
                retargetLinks(this.readonlyElementRef.el);
            });
        }

        if (this.props.cssAssetId) {
            onWillStart(async () => {
                this.cssAsset = await getBundle(this.props.cssAssetId);
            });
        }
    }

    get showIframe() {
        return this.props.hasFullHtml || this.props.cssAssetId;
    }

    /**
     * Allows overrides to process the value used in the Html Viewer.
     *
     * @param { Markup } value
     * @returns { Markup }
     */
    formatValue(value) {
        return value;
    }

    updateIframeContent(content) {
        const contentWindow = this.iframeRef.el.contentWindow;
        const iframeTarget = this.props.hasFullHtml
            ? contentWindow.document.documentElement
            : contentWindow.document.querySelector("#iframe_target");
        iframeTarget.innerHTML = content;
        retargetLinks(iframeTarget);
    }

    onLoadIframe(value) {
        const contentWindow = this.iframeRef.el.contentWindow;
        if (!this.props.hasFullHtml) {
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
}
