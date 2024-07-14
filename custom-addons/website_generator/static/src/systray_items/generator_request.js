/** @odoo-module **/

import {registry} from "@web/core/registry";
import {Component, useState, onWillStart, onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {session} from "@web/session";

export class GeneratorRequest extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            globeExtraClasses: "",
        });

        onWillStart(async () => {
            this.checkRequestStatus();
            this.interval = setInterval(() => {
                this.checkRequestStatus();
            }, 60000);
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
GeneratorRequest.template = "website_generator.GeneratorRequest";

const systrayItem = {
    Component: GeneratorRequest,
    isDisplayed: () => session.show_scraper_systray,
};

registry.category("website_systray").add("GeneratorRequest", systrayItem);
registry.category("systray").add("GeneratorRequest", systrayItem);
