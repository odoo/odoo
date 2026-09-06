import { useProps, t } from "@odoo/owl";
import { NavBar } from "@web/webclient/navbar/navbar";
import { _t } from "@web/core/l10n/translation";

export class MySubscriptionNavBar extends NavBar {
    static template = "MySubscription.NavBar";
    static components = { ...NavBar.components };

    props = useProps({
        hasSubscription: t.boolean(),
    });

    setup() {
        super.setup();
        this.hm = this.env.services.home_menu;
    }

    onClickIcon() {
        if (!this.hm) { return };
        this.hm.toggle(true);
    }

    get currentApp() {
        return {
            id: "mysubscription_app",
            name: _t("My Subscription"),
            appID: "mysubscription_app",
            actionID: "mysubscription.action_mysubscription_dashboard",
            webIconData: "/mysubscription/static/src/img/odoo_o.svg",
        };
    }

    get currentAppSections() {
        return [];
    }

}
