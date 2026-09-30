import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { x2ManyCommands } from "@web/core/orm_service";
import { useTagNavigation } from "@web/core/record_selectors/tag_navigation_hook";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} channel
 * @extends {Component<Props, Env>}
 */
export class ExpertiseTagsAutocomplete extends Component {
    static template = "im_livechat.ExpertiseTagsAutocomplete";
    static props = ["channel", "disabled?"];
    static components = { TagsList, Many2XAutocomplete };

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.store = useService("mail.store");
        useTagNavigation("root", {
            delete: (index) => {
                const expertise = this.props.channel.livechat_expertise_ids[index];
                if (expertise) {
                    this.writeExpertises([x2ManyCommands.unlink(expertise.id)]);
                }
            },
        });
    }

    /** @param {(ReturnType<typeof x2ManyCommands.link>|ReturnType<typeof x2ManyCommands.unlink>)[]} ormCommands */
    writeExpertises(ormCommands) {
        rpc("/im_livechat/conversation/write_expertises", {
            channel_id: this.props.channel.id,
            orm_commands: ormCommands,
        });
    }

    /** @param {string} name */
    createAndLinkExpertise(name) {
        if (
            this.props.channel.livechat_expertise_ids.some(
                (expertise) => expertise.name === name.trim()
            )
        ) {
            return;
        }
        rpc("/im_livechat/conversation/create_and_link_expertise", {
            channel_id: this.props.channel.id,
            expertise_name: name,
        });
    }

    /** @param {{id: number, display_name: string}} expertises */
    addExpertises(expertises) {
        const toAdd = expertises.filter((expertise) => !this.isSelected(expertise.id));
        if (!toAdd.length) {
            return;
        }
        this.writeExpertises(toAdd.map((expertise) => x2ManyCommands.link(expertise.id)));
    }

    get placeholder() {
        if (this.props.channel.livechat_expertise_ids.length === 0) {
            return _t("Add expertise");
        }
        return "";
    }

    get tags() {
        return this.props.channel.livechat_expertise_ids.map((expertise) => ({
            id: expertise.id,
            onDelete: () => this.writeExpertises([x2ManyCommands.unlink(expertise.id)]),
            text: expertise.name,
        }));
    }

    isSelected(expertiseId) {
        return this.props.channel.livechat_expertise_ids.some((e) => e.id === expertiseId);
    }
}
