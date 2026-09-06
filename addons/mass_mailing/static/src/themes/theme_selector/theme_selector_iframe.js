import { ThemeSelector } from "./theme_selector";
import {
    Component,
    markup,
    onMounted,
    onWillUnmount,
    status,
    proxy,
    signal,
    useApp,
    useOnChange,
    useScope,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { renderToFragment } from "@web/core/utils/render";
import { localization } from "@web/core/l10n/localization";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { loadIframe, loadIframeBundles } from "@mail/convert_inline/iframe_utils";

export class ThemeSelectorIframe extends Component {
    static template = "mass_mailing.ThemeSelectorIframe";
    static props = {
        config: Object,
    };

    app = useApp();

    iframeRef = signal.ref();

    setup() {
        this.themeService = useService("mass_mailing.themes");
        this.orm = useService("orm");
        this.state = proxy({
            show: false,
        });
        this.themeSelectorProps = {
            templateThemes: proxy({
                promise: undefined,
            }),
        };
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
                this.themeSelectorProps.templateThemes.promise = this.fetchTemplateThemes(
                    this.props
                );
            },
            { initialRun: false }
        );
    }

    get isBrowserSafari() {
        return isBrowserSafari();
    }

    getTemplatesDomain(props) {
        return props.config.filterTemplates
            ? [["mailing_model_id", "=", props.config.mailingModelId]]
            : [];
    }

    getThemeSelectorProps() {
        Object.assign(this.themeSelectorProps, {
            config: this.props.config,
            themesPromise: this.themeService.load(),
            iframeRef: this.iframeRef,
        });
        this.themeSelectorProps.templateThemes.promise = this.fetchTemplateThemes(this.props);
        return this.themeSelectorProps;
    }

    async fetchTemplateThemes(props) {
        const templates = await this.orm.call("mailing.mailing", "action_fetch_templates", [
            this.getTemplatesDomain(props),
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
                    props: this.getThemeSelectorProps(),
                });
                return Promise.all([
                    this.loadIframeAssets(),
                    this.themeSelectorRoot.mount(this.iframeRef().contentDocument.body),
                ]);
            });
        } catch (error) {
            loadingError = error;
        }
        if (status(this) === "destroyed") {
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
