import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSelectCreate } from "@web/views/fields/relational_utils";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class DiscussChannelMemberListField extends X2ManyField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.selectPartners = useSelectCreate({
            activeActions: { create: false, link: true },
            onSelected: async (partnerIds) => {
                for (const partnerId of partnerIds) {
                    await this.list.addNewRecord({
                        context: { default_partner_id: partnerId },
                        mode: "readonly",
                    });
                }
            },
            resModel: "res.partner",
        });
    }

    /**
     * @param {Object} [params={}]
     * @param {Object} [params.context]
     */
    async onAdd({ context } = {}) {
        if (!makeContext([this.props.context, context]).add_members) {
            return super.onAdd(...arguments);
        }
        if (!(await this.props.record.save())) {
            return;
        }
        const domain = await this.orm.call(
            this.props.record.resModel,
            "get_invite_partner_domain",
            [[this.props.record.resId]]
        );
        return this.selectPartners({ domain, title: _t("Add Members") });
    }
}

export const discussChannelMemberListField = {
    ...x2ManyField,
    component: DiscussChannelMemberListField,
    displayName: _t("Channel Members"),
    supportedTypes: ["one2many"],
};

registry.category("fields").add("discuss_channel_member_list", discussChannelMemberListField);
