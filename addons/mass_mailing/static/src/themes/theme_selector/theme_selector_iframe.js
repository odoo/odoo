import { loadIframe, loadIframeBundles } from "@mail/convert_inline/iframe_utils";
import {
    asyncComputed,
    Component,
    markup,
    onMounted,
    onWillUnmount,
    signal,
    t,
    useApp,
    usePlugin,
    useProps,
    useScope,
} from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";
import { ORM } from "@web/core/orm_plugin";
import { renderToFragment } from "@web/core/utils/render";
import { ThemeSelector } from "./theme_selector";

export class ThemeSelectorIframe extends Component {
    static template = "mass_mailing.ThemeSelectorIframe";

    props = useProps({
        config: t.object({
            filterTemplates: t.boolean().optional(),
            mailingModelId: t.or([t.number(), t.literal(false)]),
        }),
    });

    app = useApp();
    scope = useScope();
    orm = usePlugin(ORM);

    isBrowserSafari = isBrowserSafari();

    iframeRef = signal.ref();
    show = signal(false);
    templates = asyncComputed(
        () =>
            this.fetchTemplateThemes(
                this.props.config.filterTemplates,
                this.props.config.mailingModelId
            ),
        {
            initial: [],
        }
    );

    setup() {
        onMounted(() => {
            this.setupIframe();
        });
        onWillUnmount(() => {
            if (this.themeSelectorRoot) {
                this.themeSelectorRoot.destroy();
            }
        });
    }

    /**
     * @param {boolean | undefined} filterTemplates
     * @param {number | false} mailingModelId
     */
    async fetchTemplateThemes(filterTemplates, mailingModelId) {
        const domain = [];
        if (filterTemplates) {
            domain.push(["mailing_model_id", "=", mailingModelId]);
        }
        const templates = await this.orm.call("mailing.mailing", "action_fetch_templates", [
            domain,
        ]);
        return templates.map((template) => ({
            bodyArch: markup(template.body_arch),
            id: template.id,
            modelId: template.mailing_model_id[0],
            modelName: template.mailing_model_id[1],
            name: `template_${template.id}`,
            nowrap: true,
            subject: template.subject,
            userId: template.user_id[0],
            userName: template.user_id[1],
            active: template.active,
        }));
    }

    renderHeadContent() {
        return renderToFragment("mass_mailing.IframeHead", this);
    }

    async setupIframe() {
        let loadingError;
        try {
            await loadIframe(this.iframeRef(), async (iframe) => {
                iframe.contentDocument.head.appendChild(this.renderHeadContent());
                iframe.contentDocument.body.style.setProperty("direction", localization.direction);

                this.themeSelectorRoot = this.app.createRoot(ThemeSelector, {
                    env: this.env,
                    props: {
                        config: this.props.config,
                        iframeRef: this.iframeRef,
                        templates: this.templates,
                    },
                });
                return Promise.all([
                    this.loadIframeAssets(),
                    this.themeSelectorRoot.mount(this.iframeRef().contentDocument.body),
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
        this.show.set(true);
    }

    loadIframeAssets() {
        return loadIframeBundles(this.iframeRef(), ["mass_mailing.assets_iframe_theme_selector"]);
    }
}
