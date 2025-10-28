import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useTagNavigation } from "@web/core/record_selectors/tag_navigation_hook";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

/**
 * @typedef {Object} Props
 * @property {import("models").DiscussChannel} channel
 * @extends {Component<Props, Env>}
 */
export class ExpertiseTagsAutocomplete extends Component {
    static template = "im_livechat.ExpertiseTagsAutocomplete";
    static props = ["channel"];
    static components = { BadgeTag, Many2XAutocomplete };

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.store = useService("mail.store");
        useTagNavigation("root", {
            delete: (index) => {
                const expertise = this.props.channel.livechat_expertise_ids[index];
                if (expertise) {
                    this.removeExpertise(expertise.id);
                }
            },
        });
    }

    /**
     * @param {number[]} expertiseIds
     * @param {{mode: "ADD" | "REMOVE"}} param1.mode
     */
    updateExpertises(expertiseIds, { mode }) {
        const idsToUpdate = expertiseIds.filter((id) =>
            mode === "REMOVE" ? this.isSelected(id) : !this.isSelected(id)
        );
        if (idsToUpdate.length === 0) {
            return;
        }
        rpc("/im_livechat/conversation/update_expertises", {
            channel_id: this.props.channel.id,
            expertise_ids: idsToUpdate,
            mode,
        });
    }

    /** @param {string} name */
    async createOrLinkExpertise(name) {
        if (
            this.props.channel.livechat_expertise_ids.some((expertise) => expertise.name === name)
        ) {
            return;
        }
        const [expertiseId] = await this.orm.call("im_livechat.expertise", "name_create", [name]);
        this.updateExpertises([expertiseId], { mode: "ADD" });
    }

    /** @param {number} expertiseId */
    isSelected(expertiseId) {
        return this.props.channel.livechat_expertise_ids.some(
            (expertise) => expertise.id === expertiseId
        );
    }

    /** @param {{id: number, display_name: string}} expertises */
    onUpdate(expertises) {
        this.updateExpertises(
            expertises.map((expertise) => expertise.id),
            { mode: "ADD" }
        );
    }

    /** @param {number} expertiseId */
    removeExpertise(expertiseId) {
        this.updateExpertises([expertiseId], { mode: "REMOVE" });
    }

    get placeholder() {
        if (this.props.channel.livechat_expertise_ids.length === 0) {
            return _t("Add expertise");
        }
        return "";
    }
}
