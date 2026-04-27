/** @odoo-module **/

import {registry} from "@web/core/registry";
import {
    Component,
    useState,
    onMounted,
    onWillStart,
    onWillUnmount,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import {redirect} from "@web/core/utils/urls";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class WebsiteGenerator extends Component {
    static template = "website_generator.WebsiteGenerator";
    static props = { ...standardActionServiceProps };
    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.website = useService("website");

        this.canCallGetResultWaitingRequests = true;
        this.state = useState({
            error: "",
        });
        onWillStart(() => this._checkRequestStatus());
        // Every 10 seconds, we ask the server to call IAP to see if the
        // scraping result is ready.
        // If it is ready, the server will process the IAP file and generate the
        // website. Once it's done, a later call of this `setInterval` loop will
        // notice it (success or error status) and act accordingly.
        onMounted(() => {
            this.interval = setInterval(() => this._checkRequestStatus(), 10000);
        });
        onWillUnmount(() => clearInterval(this.interval));

        useBus(this.website.bus, "HIDE-WEBSITE-LOADER", () => {
            if (!this.state.error) {
                redirect("/odoo?showWebsiteGeneratorNotification=1");
            }
        });
    }
    async _checkRequestStatus() {
        // Get scraping request
        const [lastScrapRequest] = await this.orm.silent.searchRead(
            "website_generator.request",
            [],
            ["id", "status", "status_message", "website_id"],
            { limit: 1, order: "id DESC" },
        );
        // Safety check, return to backend if no request
        if (!lastScrapRequest) {
            redirect("/odoo");
            return;
        }
        // If no real error status but not yet ready, ask server to check for
        // results
        if (["error_request_still_processing", "error_maintenance", "waiting"]
                .includes(lastScrapRequest.status)) {
            if (this.canCallGetResultWaitingRequests) {
                this.canCallGetResultWaitingRequests = false;
                this.lastGetResultWaitingRequests = this.orm.call(
                    "website_generator.request",
                    "get_result_waiting_requests"
                ).then(() => {
                    this.canCallGetResultWaitingRequests = true;
                });
            }
            this._showWebsiteLoader();
            return;
        }
        // At this point, either the request is in real error or succeeded:
        // mark it as result "seen"
        this.orm.silent.write(
            "website_generator.request",
            [lastScrapRequest.id],
            {notified: true},
        );
        // If it's in error, adapt screen message to show the error
        if (lastScrapRequest.status.includes("error")) {
            this.state.error = lastScrapRequest.status_message;
            clearInterval(this.interval);
            this.website.hideLoader();
            return;
        }

        this.website.prepareOutLoader();

        // If it succeeded, redirect to the website
        window.location.href = `/website/force/${lastScrapRequest.website_id[0]}`;
    }

    _showWebsiteLoader() {
        this.website.showLoader({
            title: _t("Importing your website."),
            bottomMessageTemplate: "website_generator.request_website_loader_bottom_message",
            showLoader: false,
            showCloseButton: true,
        });
    }
}

registry.category("actions").add("website_generator", WebsiteGenerator);
