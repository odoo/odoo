import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    status,
    useEffect,
    proxy,
    signal,
    useScope,
    providePlugins,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { TemplatePreviewField } from "../../fields/template_preview_field/template_preview_field";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { KeepLast } from "@web/core/utils/concurrency";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { StyleSheetPlugin } from "../../views/mailing_template_kanban_view/stylesheets_plugin";
import { getStyleSheets } from "../../utils/iframe_assets";

export class ThemeSelector extends Component {
    static template = "mass_mailing.ThemeSelector";
    static props = {
        config: { type: Object },
        themesPromise: Promise,
        // Reactive wrapper for templateThemes promise: { promise }
        templateThemes: Object,
        iframeRef: { type: Function },
    };
    static components = {
        TemplatePreviewField,
    };

    themeSelectorWrapperRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.themeService = useService("mass_mailing.themes");
        const scope = useScope();
        providePlugins([StyleSheetPlugin], {
            styleSheetPromises: [
                getStyleSheets(scope, this.props.iframeRef(), "mass_mailing.assets_iframe_style"),
                getStyleSheets(
                    scope,
                    this.props.iframeRef(),
                    "mass_mailing.assets_theme_selector_template_shadowdom"
                ),
            ],
        });
        this.config = this.props.config;
        this.commonThemes = this.themeService.getCommonThemes();
        this.simpleThemes = this.themeService.getSimpleThemes();
        this.state = proxy({
            loading: false,
            templates: [],
            showBanner: !this.props.config.isTemplate,
        });
        onWillStart(async () => {
            const { themesPromise, templateThemes } = this.props;
            const [templates] = await Promise.all([templateThemes.promise, themesPromise]);
            Object.assign(this.state, { templates });
        });
        let templateThemesPromise = this.props.templateThemes.promise;
        const keepLastTemplateThemes = new KeepLast();
        useEffect(async () => {
            if (status(this) === "destroyed") {
                return;
            }
            if (templateThemesPromise !== this.props.templateThemes.promise) {
                templateThemesPromise = this.props.templateThemes.promise;
                this.state.loading = true;
                const templates = await keepLastTemplateThemes.add(templateThemesPromise);
                Object.assign(this.state, { templates });
                this.state.loading = false;
            }
        });
        this.throttledResize = useThrottleForAnimation(() => {
            if (status(this) === "destroyed") {
                return;
            }
            const iframe = this.props.iframeRef();
            iframe.style.width = "";
            const height = Math.trunc(
                this.themeSelectorWrapperRef().getBoundingClientRect().height
            );

            // If reducing the size of the frame would cause the scrollable element to become unscrollable,
            // then we don't resize the frame down to avoid flickering on Chromium-based browsers.
            const scrollable = closestScrollableY(iframe);
            const scrollableRange = scrollable
                ? scrollable.scrollHeight - scrollable.clientHeight
                : 0;
            let adjustHeight = true;
            if (
                scrollable &&
                iframe.style.height &&
                iframe.clientHeight - height >= scrollableRange &&
                iframe.clientHeight - height - scrollableRange < 20
            ) {
                adjustHeight = false;
            }
            if (adjustHeight) {
                iframe.style.height = height + "px";
            }
        });
        onMounted(() => {
            this.htmlResizeObserver = new ResizeObserver(this.throttledResize);
            this.htmlResizeObserver.observe(this.themeSelectorWrapperRef());
        });
        onWillUnmount(() => {
            this.htmlResizeObserver.disconnect();
        });
    }

    onSelectTemplate(html) {
        if (this.state.loading) {
            return;
        }
        this.props.config.setThemeHTML(html);
    }

    onSelectTheme(themeOptions) {
        if (this.state.loading) {
            return;
        }
        this.props.config.setThemeHTML(themeOptions.html);
    }
}
