/** @odoo-module */

import { Component, onWillStart, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { formatDuration } from "@web/core/l10n/dates";

export class ExhibitorConnectClosedDialog extends Component {
    static template = "website_event_exhibitor.ExhibitorConnectClosedDialog";
    static components = { Dialog };
    static props = {
        sponsorId: Number,
    };

    setup() {
        this.rpc = useService("rpc");

        onWillStart(() => this.fetchSponsor());
    }

    /**
     * @private
     */
    async fetchSponsor() {
        const sponsorData = await this.rpc(
            `/event_sponsor/${encodeURIComponent(this.props.sponsorId)}/read`
        );
        sponsorData.website_description = markup(sponsorData.website_description);
        this.formatEventStartRemaining = formatDuration(sponsorData.event_start_remaining, true);
        this.sponsorData = sponsorData;
    }
}
