odoo.define('systray.systray_odoo_referral', function (require) {
    "use strict";

    const localStorage = require('web.local_storage');
    const SystrayMenu = require('web.SystrayMenu');

    class ActionMenu extends owl.Component {

        async mounted(parent) {
            const lastFetch = localStorage.getItem("odoo_referral.updates_last_fetch");
            const updatesCount = localStorage.getItem("odoo_referral.updates_count");
            const hasClicked = localStorage.getItem("odoo_referral.has_clicked");
            if (
                hasClicked &&
                (!lastFetch ||
                    Date(parseInt(lastFetch)) < Date(new Date().getTime() - 24 * 60 * 60 * 1000))
            ) {
                const count = await this.env.services.rpc(
                    {
                        model: "res.users",
                        method: "get_referral_updates_count_for_current_user",
                    },
                    {
                        shadow: true,
                    }
                );
                localStorage.setItem("odoo_referral.updates_last_fetch", Date.now());
                localStorage.setItem("odoo_referral.updates_count", count);
                if (count > 0) {
                    this.el.querySelector(".o_notification_counter").innerText = count;
                }
            } else {
                if (updatesCount && updatesCount > 0) {
                    this.el.querySelector(".o_notification_counter").innerText = updatesCount;
                }
            }
            return super.mounted(...arguments);
        }

        async onClickGiftIcon() {
            localStorage.setItem("odoo_referral.updates_count", 0);
            const result = await this.env.services.rpc({
                route: "/odoo_referral/go/",
            });
            localStorage.setItem("odoo_referral.has_clicked", 1);
            this.el.querySelector(".o_notification_counter").innerText = "";
            const w = window.open(result.link, "_blank", "noreferrer noopener");
            if (!w || w.closed || typeof w.closed === "undefined") {
                const message = this.env._t(
                    "A popup window has been blocked. You " +
                        "may need to change your browser settings to allow " +
                        "popup windows for this page."
                );
                this.env.services.notification.notify({
                    type: "danger",
                    message: message,
                    sticky: true,
                });
            }
        }
    }

    ActionMenu.template = "systray_odoo_referral.gift_icon";

    SystrayMenu.Items.push(ActionMenu);
    return ActionMenu;
});
