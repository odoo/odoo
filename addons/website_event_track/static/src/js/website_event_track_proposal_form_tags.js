import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import publicWidget from "@web/legacy/js/public/public_widget";
import { attachComponent } from "@web_editor/js/core/owl_utils";

class WebsiteEventTrackProposalFormTagsWrapper extends Component {
    static template = "website_event_track.WebsiteEventTrackProposalFormTagsWrapper";
    static components = { SelectMenu };
    static props = {
        placeholder: { optional: true, type: String },
        defaultChoices: { optional: true, type: Array },
    };

    setup() {
        this.state = useState({
            ...this.props,
            value: [],
        });
    }
    onSelect(item) {
        this.state.value = item;
    }
}

publicWidget.registry.websiteEventTrackProposalFormTags = publicWidget.Widget.extend({
    selector: '.o_website_event_track_proposal_form_tags',

    async willStart() {
        const choices = await rpc("/event/track_tag/search_read", {
            fields: ["id", "name", "category_id"],
            domain: [],
        });
        this.choices = choices.map(({ id, category_id, name }) => {
            return {
                value: id,
                label: category_id ? `${category_id[1]} : ${name}` : name,
            };
        });
    },

    async start() {
        await this._super(...arguments);
        await attachComponent(this, this.el, WebsiteEventTrackProposalFormTagsWrapper, {
            defaultChoices: this.choices || [],
            placeholder: _t("Select Categories"),
        });
    },
});

export default publicWidget.registry.websiteEventTrackProposalFormTags;
