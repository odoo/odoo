import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ThemeSelector extends Component {
    static template = "mass_mailing.ThemeSelector";
    static props = {
        config: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.themeService = useService("mass_mailing.themes");
        this.config = this.props.config;
        this.themes = this.themeService.getThemes();
        this.favoriteTemplates = useState([]);
        onWillStart(async () => {
            const themeServicePromise = this.themeService.load();
            const favoritePromise = this.orm.call("mailing.mailing", "action_fetch_favorites", [
                this.favoriteDomain,
            ]);
            const [favoriteTemplates] = await Promise.all([favoritePromise, themeServicePromise]);
            Object.assign(
                this.favoriteTemplates,
                favoriteTemplates.map((favorite) => ({
                    html: favorite.body_arch,
                    id: favorite.id,
                    modelId: favorite.mailing_model_id[0],
                    modelName: favorite.mailing_model_id[1],
                    name: `template_${favorite.id}`,
                    nowrap: true,
                    subject: favorite.subject,
                    userId: favorite.user_id[0],
                    userName: favorite.user_id[1],
                }))
            );
        });
    }

    get favoriteDomain() {
        return this.props.config.filterTemplates
            ? [["mailing_model_id", "=", this.props.config.mailingModelId]]
            : [];
    }

    async onRemoveFavorite(index) {
        const favorite = this.favoriteTemplates[index];
        if (!favorite) {
            return;
        }
        const notificationAction = await this.orm.call(
            "mailing.mailing",
            "action_remove_favorite",
            [favorite.id]
        );
        this.favoriteTemplates.splice(index, 1);
        this.action.doAction(notificationAction);
    }

    onSelectFavorite(html) {
        this.props.config.setThemeHTML(html);
    }

    onSelectTheme(themeOptions) {
        this.props.config.setThemeHTML(themeOptions.html);
    }
}
