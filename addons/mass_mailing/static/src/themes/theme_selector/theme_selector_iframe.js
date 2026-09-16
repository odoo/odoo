import { loadIframe, loadIframeBundles } from "@mail/convert_inline/iframe_utils";
import {
    Component,
    markup,
    onMounted,
    onWillUnmount,
    proxy,
    signal,
    t,
    useApp,
    useOnChange,
    useProps,
    useScope,
} from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";
import { renderToFragment } from "@web/core/utils/render";
import { ThemeSelector } from "./theme_selector";

export class ThemeSelectorIframe extends Component {
    static template = "mass_mailing.ThemeSelectorIframe";

    props = useProps({
        config: t.object(),
    });

    app = useApp();

    iframeRef = signal.ref();
    templateThemesPromise = signal(null);

    setup() {
        this.themeService = useService("mass_mailing.themes");
        this.orm = useService("orm");
        this.state = proxy({
            show: false,
        });
        this.scope = useScope();
        onMounted(() => {
            this.setupIframe();
        });
        onWillUnmount(() => {
            if (this.themeSelectorRoot) {
                this.themeSelectorRoot.destroy();
            }
        });
        useOnChange(
            () => [this.props.config.mailingModelId],
            () => {
                this.templateThemesPromise.set(this.fetchTemplateThemes());
            },
            { initialRun: false }
        );
    }

    get isBrowserSafari() {
        return isBrowserSafari();
    }

    getTemplatesDomain() {
        return this.props.config.filterTemplates
            ? [["mailing_model_id", "=", this.props.config.mailingModelId]]
            : [];
    }

    async fetchTemplateThemes() {
        const templates = await this.orm.call("mailing.mailing", "action_fetch_templates", [
            this.getTemplatesDomain(),
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

                const themesPromise = this.themeService.load();
                this.templateThemesPromise.set(this.fetchTemplateThemes());

                this.themeSelectorRoot = this.app.createRoot(ThemeSelector, {
                    env: this.env,
                    props: {
                        config: this.props.config,
                        iframeRef: this.iframeRef,
                        templateThemesPromise: this.templateThemesPromise,
                        themesPromise: themesPromise,
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
        this.state.show = true;
    }

    loadIframeAssets() {
        return loadIframeBundles(this.iframeRef(), ["mass_mailing.assets_iframe_theme_selector"]);
    }
}
