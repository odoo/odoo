import { ThemeSelector } from "./theme_selector";
import { assets, AssetsLoadingError, getBundle, loadBundle } from "@web/core/assets";
import {
    Component,
    markup,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    reactive,
    status,
    useRef,
    useState,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { renderToFragment } from "@web/core/utils/render";
import { localization } from "@web/core/l10n/localization";
import { browser } from "@web/core/browser/browser";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

const CSSSheetsCache = new Map();

export class ThemeSelectorIframe extends Component {
    static template = "mass_mailing.ThemeSelectorIframe";
    static props = {
        config: Object,
    };

    setup() {
        this.themeService = useService("mass_mailing.themes");
        this.orm = useService("orm");
        this.state = useState({
            show: false,
        });
        this.themeSelectorProps = {
            favoriteThemes: reactive({
                promise: undefined,
            }),
        };
        this.iframeRef = useRef("iframe");
        onMounted(() => {
            if (this.iframeRef.el.contentDocument.readyState === "complete") {
                this.setupIframe();
            } else {
                // Browsers like Firefox only make iframe document available after dispatching "load"
                this.iframeRef.el.addEventListener("load", () => this.setupIframe(), {
                    once: true,
                });
            }
        });
        onWillUnmount(() => {
            if (this.themeSelectorRoot) {
                this.themeSelectorRoot.destroy();
            }
        });
        onWillUpdateProps((newProps) => {
            if (newProps.config.mailingModelId !== this.props.config.mailingModelId) {
                this.themeSelectorProps.favoriteThemes.promise = this.fetchFavoriteThemes(newProps);
            }
        });
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
            styleSheetsPromise: this.getStyleSheets(),
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
        this.iframeRef.el.contentDocument.head.appendChild(this.renderHeadContent());
        this.iframeRef.el.contentDocument.body.style.setProperty(
            "direction",
            localization.direction
        );
        this.themeSelectorRoot = this.__owl__.app.createRoot(ThemeSelector, {
            props: this.getThemeSelectorProps(),
        });
        await Promise.all([
            loadBundle("mass_mailing.assets_iframe_theme_selector", {
                targetDoc: this.iframeRef.el.contentDocument,
                css: true,
                js: false,
            }),
            this.themeSelectorRoot.mount(this.iframeRef.el.contentDocument.body),
        ]);
        browser.requestAnimationFrame(() => {
            if (status(this) !== "destroyed") {
                this.state.show = true;
            }
        });
    }

    /**
     * Get common stylesheets used for every favorite mail template
     *
     * @returns {Promise<Array<CSSStyleSheet>>}
     */
    async getStyleSheets() {
        const { cssLibs } = await getBundle("mass_mailing.assets_iframe_style");
        const loadCSSPromises = [];
        if (cssLibs) {
            loadCSSPromises.push(...cssLibs.map((url) => this.loadCSSSheets(url)));
        }
        const cssTexts = await Promise.all(loadCSSPromises);
        const sheetPromises = [];
        for (const cssText of cssTexts) {
            const sheet = new this.iframeRef.el.contentDocument.defaultView.CSSStyleSheet();
            sheetPromises.push(sheet.replace(cssText).then(() => sheet));
        }
        return Promise.all(sheetPromises);
    }

    /**
     * Custom load which does not add the CSSStyleSheet in the current document
     */
    loadCSSSheets(url, retryCount = 0) {
        if (CSSSheetsCache.has(url)) {
            return CSSSheetsCache.get(url);
        }
        const promise = new Promise((resolve, reject) =>
            fetch(url)
                .then((response) => {
                    if (!response.ok) {
                        reject(
                            new AssetsLoadingError(`The loading of ${url} failed`, {
                                cause: response.status,
                            })
                        );
                    }
                    return response.text();
                })
                .then(resolve)
                .catch(async (error) => {
                    CSSSheetsCache.delete(url);
                    if (retryCount < assets.retries.count) {
                        const delay = assets.retries.delay + assets.retries.extraDelay * retryCount;
                        await new Promise((res) => setTimeout(res, delay));
                        this.loadCSSSheets(url, retryCount + 1)
                            .then(resolve)
                            .catch((reason) => {
                                CSSSheetsCache.delete(url);
                                reject(reason);
                            });
                    } else {
                        reject(
                            new AssetsLoadingError(`The loading of ${url} failed`, { cause: error })
                        );
                    }
                })
        );
        CSSSheetsCache.set(url, promise);
        return promise;
    }
}
