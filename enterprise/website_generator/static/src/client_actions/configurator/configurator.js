import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import {
    ROUTES,
    Configurator,
    SkipButton,
} from "@website/client_actions/configurator/configurator";
import { WEBSITE_GENERATOR_ROUTE } from "@website_enterprise/client_actions/configurator/configurator";

ROUTES.websiteGenerator = WEBSITE_GENERATOR_ROUTE; // TODO: make these urls prettier?

export class WebsiteGeneratorScreen extends Component {
    static components = { SkipButton };
    static template = "website_generator.Configurator.WebsiteGeneratorScreen";
    static props = {
        navigate: Function,
        skip: Function,
    };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.ui = useService("ui");
    }

    async makeWebsiteGeneratorRequest(ev) {
        ev.preventDefault();
        // We have to get the form data before disabling inputs.
        const formData = new FormData(ev.currentTarget);
        const data = Object.fromEntries(formData.entries());
        this.ui.block();
        let result;
        try {
            result = await this.orm.call("website", "import_website", [], data);
        } finally {
            if (!result) {
                this.ui.unblock();
            }
        }

        if (result) {
            this.action.doAction({
                type: "ir.actions.act_url",
                url: "/odoo/action-website_generator.website_generator_screen?reload=true",
                target: "self",
            });
        } else {
            this.notification.add(result, {
                title: _t("Something went wrong while importing your website."),
            });
        }
    }
}

patch(Configurator, {
    components: {
        ...Configurator.components,
        WebsiteGeneratorScreen,
    },
});
