/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import { user } from "@web/core/user";
import {Component, useState, onMounted, onWillStart, onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {session} from "@web/session";

export class GeneratorRequest extends Component {
    static template = "website_generator.GeneratorRequest";
    static props = {};
    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({
            globeExtraClasses: "",
        });

        onWillStart(async () => {
            this.checkRequestStatus();
            const searchParams = new URLSearchParams(window.location.search);

            if (searchParams.get("showWebsiteGeneratorNotification")) {
                // TODO: find a better way to show this notification
                const users = await this.orm.read("res.partner", [user.partnerId], ["email"]);
                const userEmail = users[0].email;
                this.notification.add(
                    _t("We will notify %(email)s when everything is ready.", { email: userEmail }),
                    {
                        title: _t("The import of your website has started!"),
                        type: "info",
                        sticky: true,
                    },
                );
            }
        });
        onMounted(() => {
            this.interval = setInterval(() => this.checkRequestStatus(), 60000);
        });
        onWillUnmount(() => {
            clearInterval(this.interval);
        });
    }
    async goToWaitingView() {
        await this.actionService.doAction("website_generator.website_generator_screen");
    }
    async checkRequestStatus() {
        const [scrapRequest] = await this.orm.silent.searchRead(
            "website_generator.request",
            [],
            ["status"],
            {limit: 1, order: "id DESC"},
        );
        if (!scrapRequest) {
            clearInterval(this.interval);
        }
        if (["error_request_still_processing", "error_maintenance", "waiting"]
                .includes(scrapRequest.status)) {
            return;
        }
        if (scrapRequest.status.includes("error")) {
            this.state.globeExtraClasses = "text-danger";
        } else {
            this.state.globeExtraClasses = "text-success";
        }
        clearInterval(this.interval);
    }
}

const systrayItem = {
    Component: GeneratorRequest,
    isDisplayed: () => session.show_scraper_systray,
};

registry.category("website_systray").add("GeneratorRequest", systrayItem);
registry.category("systray").add("GeneratorRequest", systrayItem);
