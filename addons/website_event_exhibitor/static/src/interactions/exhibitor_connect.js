import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { redirect } from "@web/core/utils/urls";
import { ExhibitorConnectClosedDialog } from "../components/exhibitor_connect_closed_dialog/exhibitor_connect_closed_dialog";

export class ExhibitorConnect extends Interaction {
    static selector = ".o_wesponsor_connect_button";
    dynamicContent = {
        _root: {
            "t-on-click.stop.prevent": this.debounced(this.onClick, 500),
        },
    };

    setup() {
        const eventIsOngoing = this.el.dataset.eventIsOngoing || false;
        const sponsorIsOngoing = this.el.dataset.sponsorIsOngoing || false;
        const userEventManager = this.el.dataset.userEventManager || false;
        this.shouldOpenDialog = !userEventManager && !(eventIsOngoing && sponsorIsOngoing);
    }

    onClick() {
        if (this.shouldOpenDialog) {
            return this.openClosedDialog();
        } else {
            redirect(this.el.dataset.sponsorUrl);
        }
    }

    openClosedDialog() {
        const sponsorId = parseInt(this.el.dataset.sponsorId);
        this.services.dialog.add(ExhibitorConnectClosedDialog, { sponsorId });
    }
}

registry
    .category("public.interactions")
    .add("website_event_exhibitor.exhibitor_connect", ExhibitorConnect);
