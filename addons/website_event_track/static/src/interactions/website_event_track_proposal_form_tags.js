import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

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

export class WebsiteEventTrackProposalFormTags extends Interaction {
    static selector = ".o_website_event_track_proposal_form_tags";

    async willStart() {
        const choices = await rpc("/event/track_tag/search_read", {
            fields: ["id", "name", "category_id"],
            domain: [["color", "!=", 0]],
        });
        const choicesMap = choices.map(({ id, category_id, name }) => {
            return {
                value: id,
                label: category_id ? `${category_id[1]} : ${name}` : name,
            };
        });
        this.mountComponent(this.el, WebsiteEventTrackProposalFormTagsWrapper, {
            defaultChoices: choicesMap || [],
            placeholder: _t("Select Categories"),
        });
    }
}

registry
    .category("public.interactions")
    .add("website_event_track.website_event_track_proposal_form_tags", WebsiteEventTrackProposalFormTags);
