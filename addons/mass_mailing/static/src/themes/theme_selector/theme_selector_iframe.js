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
import { getStyleSheets } from "../../util/assets_utils";

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
            favoriteThemes: proxy({
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
                this.themeSelectorProps.favoriteThemes.promise = this.fetchFavoriteThemes(this.props);
            },
            { initialRun: false }
        );
    }

    get isBrowserSafari() {
        return isBrowserSafari();
    }

    getFavoriteDomain(props) {
        return props.config.filterTemplates
            ? [["mailing_model_id", "=", props.config.mailingModelId]]
            : [];
    }

    getThemeSelectorProps() {
        Object.assign(this.themeSelectorProps, {
            config: this.props.config,
            styleSheetsPromise: getStyleSheets(
                this.scope,
                this.iframeRef(),
                "mass_mailing.assets_iframe_style"
            ),
            themesPromise: this.themeService.load(),
            iframeRef: this.iframeRef,
        });
        this.themeSelectorProps.favoriteThemes.promise = this.fetchFavoriteThemes(this.props);
        return this.themeSelectorProps;
    }

    async fetchFavoriteThemes(props) {
        const favoriteTemplates = await this.orm.call("mailing.mailing", "action_fetch_favorites", [
            this.getFavoriteDomain(props),
        ]);
        return favoriteTemplates.map((favorite) => ({
            bodyArch: markup(favorite.body_arch),
            id: favorite.id,
            modelId: favorite.mailing_model_id[0],
            modelName: favorite.mailing_model_id[1],
            name: `template_${favorite.id}`,
            nowrap: true,
            subject: favorite.subject,
            userId: favorite.user_id[0],
            userName: favorite.user_id[1],
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
