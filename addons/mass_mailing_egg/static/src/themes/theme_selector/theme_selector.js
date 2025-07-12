import { Component, markup, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * TODO EGGMAIL: maybe remove the t-key and config to use normal props/willupdateprops
 */
export class ThemeSelector extends Component {
    static template = "mass_mailing_egg.ThemeSelector";
    static props = {
        config: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        // TODO EGGMAIL: currently depends on the parent component to load themes, maybe clean that up
        this.themeService = useService("mass_mailing_egg.themes");
        this.config = this.props.config;
        this.themes = this.themeService.getThemes();
        this.favoriteTemplates = useState([]);
        onWillStart(async () => {
            const favoriteTemplates = await this.orm.call(
                "mailing.mailing",
                "action_fetch_favorites",
                [this.favoriteDomain]
            );
            Object.assign(
                this.favoriteTemplates,
                favoriteTemplates.map((favorite) => ({
                    html: markup(favorite.body_arch),
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

    onSelectTheme(html) {
        const themeOptions = {
            ...this.themeService.getThemeOptions(html),
        };
        this.props.config.setThemeOptions(themeOptions);
    }
}
