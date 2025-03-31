/** @odoo-module */

import { Component, onWillStart, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { formatDuration } from "@web/core/l10n/dates";

export class ExhibitorConnectClosedDialog extends Component {
    static template = "website_event_exhibitor.ExhibitorConnectClosedDialog";
    static components = { Dialog };
    static props = {
        sponsorId: Number,
    };

    setup() {
        onWillStart(() => this.fetchSponsor());
    }

    /**
     * @private
     */
    async fetchSponsor() {
        const sponsorData = await rpc(
            `/event_sponsor/${encodeURIComponent(this.props.sponsorId)}/read`
        );
        // empty string on falsy so markup doesn't create a "false" string
        sponsorData.website_description = sponsorData.website_description || "";
        sponsorData.website_description = markup(sponsorData.website_description);
        this.formatEventStartRemaining = formatDuration(sponsorData.event_start_remaining, true);
        this.sponsorData = sponsorData;
    }
}
