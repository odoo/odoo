import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ROUTES, WelcomeScreen } from "@website/client_actions/configurator/configurator";

export const WEBSITE_GENERATOR_ROUTE = 6;

patch(WelcomeScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.ui = useService("ui");

        onWillStart(async () => {
            this.showWebsiteGeneratorButton = await this.orm.call(
                "website",
                "is_website_generator_available",
            );
        });
    },

    async goToWebsiteGeneratorRequest() {
        if (ROUTES.websiteGenerator) {
            this.props.navigate(ROUTES.websiteGenerator);
            return;
        }

        // install website_generator
        this.ui.block();
        const modules = await this.orm.searchRead(
            "ir.module.module",
            [["name", "=", "website_generator"]],
            ["id"],
        );
        await this.orm.call("ir.module.module", "button_immediate_install", [[modules[0].id]]);
        this.props.navigate(WEBSITE_GENERATOR_ROUTE, true);
        this.ui.unblock();
    },
});
