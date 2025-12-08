import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    status,
    useRef,
    useState,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FavoritePreview } from "./favorite_preview";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { effect } from "@web/core/utils/reactive";
import { KeepLast } from "@web/core/utils/concurrency";
import { _t } from "@web/core/l10n/translation";

export class ThemeSelector extends Component {
    static template = "mass_mailing.ThemeSelector";
    static props = {
        config: { type: Object },
        styleSheetsPromise: Promise,
        themesPromise: Promise,
        // Reactive wrapper for favoriteThemes promise: { promise }
        favoriteThemes: Object,
        iframeRef: Object,
    };
    static components = {
        FavoritePreview,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.themeService = useService("mass_mailing.themes");
        this.themeSelectorWrapperRef = useRef("themeSelectorWrapper");
        this.config = this.props.config;
        this.commonThemes = this.themeService.getCommonThemes();
        this.simpleThemes = this.themeService.getSimpleThemes();
        this.state = useState({
            loading: false,
            favoriteTemplates: [],
        });
        onWillStart(async () => {
            const { themesPromise, favoriteThemes } = this.props;
            const [favoriteTemplates] = await Promise.all([favoriteThemes.promise, themesPromise]);
            Object.assign(this.state, { favoriteTemplates });
        });
        let favoriteThemesPromise = this.props.favoriteThemes.promise;
        const keepLastFavoriteThemes = new KeepLast();
        effect(
            async (favoriteThemes) => {
                if (status(this) === "destroyed") {
                    return;
                }
                if (favoriteThemesPromise !== favoriteThemes.promise) {
                    favoriteThemesPromise = favoriteThemes.promise;
                    this.state.loading = true;
                    const favoriteTemplates = await keepLastFavoriteThemes.add(
                        favoriteThemesPromise
                    );
                    Object.assign(this.state, { favoriteTemplates });
                    this.state.loading = false;
                }
            },
            [this.props.favoriteThemes]
        );
        this.throttledResize = useThrottleForAnimation(() => {
            if (status(this) === "destroyed") {
                return;
            }
            const iframe = this.props.iframeRef.el;
            iframe.style.width = "";
            const height = Math.trunc(
                this.themeSelectorWrapperRef.el.getBoundingClientRect().height
            );
            iframe.style.height = height + "px";
        });
        onMounted(() => {
            this.htmlResizeObserver = new ResizeObserver(this.throttledResize);
            this.htmlResizeObserver.observe(this.themeSelectorWrapperRef.el);
        });
        onWillUnmount(() => {
            this.htmlResizeObserver.disconnect();
        });
    }

    async onRemoveFavorite(ev, index) {
        ev.stopPropagation();
        const favorite = this.state.favoriteTemplates[index];
        if (this.state.loading || !favorite) {
            return;
        }
        await this.orm.write("mailing.mailing", [favorite.id], { favorite: false });
        this.state.favoriteTemplates.splice(index, 1);
        this.action.doAction({
            type: "ir.actions.client",
            tag: "display_notification",
            params: {
                message: _t("Design removed from the templates!"),
                next: { type: "ir.actions.act_window_close" },
                sticky: false,
                type: "info",
            },
        });
    }

    onSelectFavorite(html) {
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
