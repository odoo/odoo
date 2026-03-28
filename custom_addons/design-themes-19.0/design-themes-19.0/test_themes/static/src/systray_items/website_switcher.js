/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from '@web/core/utils/hooks';
import { WebsiteSwitcherSystrayItem } from "@website/client_actions/website_preview/website_switcher_systray_item";
import { onMounted, useState } from "@odoo/owl";

patch(WebsiteSwitcherSystrayItem.prototype, {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.tooltips = useState({});
        // Disable the notification service to avoid having a notification for each theme.
        this.notificationService = { add: () => () => null };

        onMounted(async () => {
            const themesWebsites = await this.orm.call('website', 'get_test_themes_websites_theme_preview');
            for (const themeId in themesWebsites) {
                this.tooltips[themeId] = {
                    "data-tooltip-template": 'test_themes.ThemeTooltip',
                    "data-tooltip-position": 'left',
                    "data-tooltip-delay": 100,
                    "data-tooltip-info": JSON.stringify({url: themesWebsites[themeId]}),
                };
            }
        });
    },

    getElements() {
        // Add tooltip information
        const elements = super.getElements(...arguments);
        return elements.map((elem) => {
            elem.dataset = {
                ...elem.dataset,
                ...this.tooltips[elem.id]
            };
            return elem;
        });
    },

    template: "test_themes.WebsiteSwitcherSystrayItem",
});
