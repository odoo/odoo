import { Component, onWillStart, markup, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { formatDuration, deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;
export class ExhibitorConnectClosedDialog extends Component {
    static template = "website_event_exhibitor.ExhibitorConnectClosedDialog";
    static components = { Dialog };
    props = useProps({
        sponsorId: t.number(),
        close: t.function(),
    });

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
        this.formatEventDateBegin = deserializeDateTime(
            sponsorData.event_date_begin,
            { tz: sponsorData.event_date_tz }
        ).toLocaleString(DateTime.DATETIME_MED);
        this.sponsorData = sponsorData;
    }
}
