import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    providePlugins,
    signal,
    t,
    useProps,
    useScope,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { closestScrollableY } from "@web/core/utils/scrolling";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { TemplatePreviewField } from "../../fields/template_preview_field/template_preview_field";
import { getStyleSheets } from "../../utils/iframe_assets";
import { StyleSheetPlugin } from "../../views/mailing_template_kanban_view/stylesheets_plugin";

export class ThemeSelector extends Component {
    static template = "mass_mailing.ThemeSelector";
    static components = {
        TemplatePreviewField,
    };

    props = useProps({
        config: t.object(),
        iframeRef: t.signal(),
        /** @type {import("@odoo/owl").AsyncComputed<Record<string, any>[]>} */
        templates: t.function(),
    });

    themeSelectorWrapperRef = signal.ref();

    get commonThemes() {
        return this.themeService.getCommonThemes();
    }

    get simpleThemes() {
        return this.themeService.getSimpleThemes();
    }

    setup() {
        this.themeService = useService("mass_mailing.themes");
        this.scope = useScope();
        providePlugins([StyleSheetPlugin], {
            styleSheetPromises: this.loadStyleSheets(),
        });

        onWillStart(() => this.themeService.load());
        onWillStart(() => this.props.templates.currentPromise());

        this.throttledResize = useThrottleForAnimation(() => {
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

    loadStyleSheets() {
        return [
            getStyleSheets(this.scope, this.props.iframeRef(), "mass_mailing.assets_iframe_style"),
            getStyleSheets(
                this.scope,
                this.props.iframeRef(),
                "mass_mailing.assets_theme_selector_template_shadowdom"
            ),
        ];
    }

    onSelectTemplate(html) {
        if (this.props.templates.loading()) {
            return;
        }
        this.props.config.setThemeHTML(html);
    }

    onSelectTheme(themeOptions) {
        if (this.props.templates.loading()) {
            return;
        }
        this.props.config.setThemeHTML(themeOptions.html);
    }
}
