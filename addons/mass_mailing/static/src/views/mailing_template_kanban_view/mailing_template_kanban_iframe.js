import { loadIframe, loadIframeBundles } from "@mail/convert_inline/iframe_utils";
import {
    Component,
    onMounted,
    onWillUnmount,
    signal,
    useApp,
    useEffect,
    useProps,
    useScope,
} from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { renderToFragment } from "@web/core/utils/render";
import { kanbanRendererProps } from "@web/views/kanban/kanban_renderer";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { MailingTemplateKanbanWrapper } from "./mailing_template_kanban_wrapper";
import { cookie } from "@web/core/browser/cookie";

/**
 * This is an Iframe in which the kanban renderer will be loaded
 * in order to securely and properly display cards with plain
 * HTML content.
 */
export class MailingTemplateKanbanIframe extends Component {
    static template = "mass_mailing.MailingTemplateKanbanIframe";

    props = useProps(kanbanRendererProps);
    app = useApp();
    iframeRef = signal.ref();
    ready = signal(false);

    setup() {
        this.scope = useScope();
        this.kanbanRendererProps = signal.Object(this.props);
        this.rendererWrapperRootProps = {
            kanbanRendererProps: this.kanbanRendererProps,
            iframeRef: this.iframeRef,
        };
        onMounted(() => {
            this.setupIframe();
        });
        onWillUnmount(() => {
            if (this.templateKanbanRoot) {
                this.templateKanbanRoot.destroy();
            }
        });
        useEffect(() => {
            this.kanbanRendererProps = this.props;
        });
    }

    get isBrowserSafari() {
        return isBrowserSafari();
    }

    renderHeadContent() {
        return renderToFragment("mass_mailing.IframeHead", this);
    }

    loadIframeAssets() {
        return loadIframeBundles(
            this.iframeRef(),
            [cookie.get("color_scheme") === "dark" ? "web.assets_web_dark" : "web.assets_web"],
            { css: true }
        );
    }

    /**
     * Load the real KanbanRenderer inside an iframe and load the
     * required assets for it.
     */
    async setupIframe(props = this.rendererWrapperRootProps) {
        let loadingError;
        try {
            await loadIframe(this.iframeRef(), async (iframe) => {
                iframe.contentDocument.head.appendChild(this.renderHeadContent());
                iframe.contentDocument.body.style.setProperty("direction", localization.direction);
                this.templateKanbanRoot = this.app.createRoot(MailingTemplateKanbanWrapper, {
                    env: this.env,
                    props: props,
                });
                await Promise.all([
                    this.loadIframeAssets(),
                    this.templateKanbanRoot.mount(this.iframeRef().contentDocument.body),
                ]);
            });
        } catch (error) {
            loadingError = error;
        }
        if (this.scope.isDestroyed()) {
            return;
        } else if (loadingError) {
            throw loadingError;
        }
        this.ready.set(true);
    }
}
