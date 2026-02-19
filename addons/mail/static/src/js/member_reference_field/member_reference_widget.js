import { registry } from "@web/core/registry";
import { ReferenceField, referenceField } from "@web/views/fields/reference/reference_field";

export class MemberReferenceField extends ReferenceField {
    static template = "mail.MemberReferenceField";

    setup() {
        const returnVal = super.setup();
        // selection is [['res.partner', 'Partner'], ['mail.guest', 'Guest']]
        // select partner by default
        const defaultSelect = this.selection?.[0][0];
        if (defaultSelect) {
            this.state.currentRelation = defaultSelect;
        }
        return returnVal;
    }

    get m2oProps() {
        const props = super.m2oProps;
        props.cssClass = `${props.cssClass ?? ''} flex-grow-1`;
        props.canCreate = false;
        props.canCreateEdit = false;
        props.canQuickCreate = false;
        if (props.readonly) {
            props.canOpen = false;
        }
        const memberPartnerIds = [];
        this.props.record._parentRecord?.data.channel_member_ids?.records.forEach(
            (record) => {
                if (record.data.member_ref?.resModel == "res.partner") {
                    memberPartnerIds.push(record.data.member_ref.resId);
                }
            }
        ) || [];
        const groupPublicId = this.props.record._parentRecord?.data.group_public_id?.id || [];
        props.domain = () => [
            ["partner_share", "=", false],
            ["id", "not in", memberPartnerIds],
            ["user_id.group_ids", "=", groupPublicId]
        ];
        return props;
    }
}

export const memberReferenceField = {
    ...referenceField,
    component: MemberReferenceField,
};

registry.category("fields").add("member_reference", memberReferenceField);
