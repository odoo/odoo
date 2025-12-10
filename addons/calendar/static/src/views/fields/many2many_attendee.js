import { AvatarTag } from "@web/core/tags_list/avatar_tag";
import { ConnectionLostError } from "@web/core/network/rpc";
import {
    Many2ManyTagsAvatarUserField,
    many2ManyTagsAvatarUserField,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { registry } from "@web/core/registry";
import { useSpecialData } from "@web/views/fields/relational_utils";

const ICON_BY_STATUS = {
    accepted: "fa-check",
    declined: "fa-times",
    tentative: "fa-question",
};

export class AttendeeTag extends AvatarTag {
    static template = "calendar.AttendeeTag";
    static props = {
        ...AvatarTag.props,
        isUnavailable: { type: Boolean, optional: true },
        noEmail: { type: Boolean, optional: true },
        status: { type: String, optional: true },
    };

    get statusIcon() {
        return ICON_BY_STATUS[this.props.status];
    }
}

export class Many2ManyAttendee extends Many2ManyTagsAvatarUserField {
    static template = "calendar.Many2ManyAttendee";
    static components = {
        ...super.components,
        Tag: AttendeeTag,
    };
    setup() {
        super.setup();
        this.specialData = useSpecialData((orm, props) => {
            const { context, name, record } = props;
            return orm
                .call(
                    "res.partner",
                    "get_attendee_detail",
                    [record.data[name].records.map((rec) => rec.resId), [record.resId || false]],
                    {
                        context,
                    }
                )
                .catch((error) => {
                    if (error instanceof ConnectionLostError) {
                        return [];
                    }
                    throw error;
                });
        });
    }

    getTagProps(record) {
        const tag = super.getTagProps(record);
        const result = {
            text: tag.text,
            tooltip: tag.tooltip,
            imageUrl: tag.imageUrl,
            onAvatarClick: tag.onAvatarClick,
            onDelete: tag.onDelete,
        };

        const partner = this.specialData.data.find((partner) => record.resId === partner.id);
        if (partner) {
            result.status = partner.status;
        }

        const noEmailPartnerIds = this.props.record.data.invalid_email_partner_ids
            ? this.props.record.data.invalid_email_partner_ids.records
            : [];
        const noEmail = noEmailPartnerIds.find(
            (noEmailPartner) => record.resId == noEmailPartner.resId
        );
        if (noEmail) {
            result.noEmail = true;
        }

        const unavailablePartnerIds = this.props.record.data.unavailable_partner_ids
            ? this.props.record.data.unavailable_partner_ids.records
            : [];
        if (
            unavailablePartnerIds.find(
                (unavailablePartner) => record.resId == unavailablePartner.resId
            )
        ) {
            result.isUnavailable = true;
        }
        return result;
    }

    get tags() {
        const tags = super.tags;
        const organizer = this.specialData.data.find((partner) => partner.is_organizer);
        if (organizer) {
            const orgId = organizer.id;
            // sort elements according to the partner id
            tags.sort((a, b) => {
                const a_org = a.resId === orgId;
                return a_org ? -1 : 1;
            });
        }
        return tags;
    }
}

export const many2ManyAttendee = {
    ...many2ManyTagsAvatarUserField,
    component: Many2ManyAttendee,
    additionalClasses: ["o_field_many2many_tags_avatar", "w-100"],
};

registry.category("fields").add("many2manyattendee", many2ManyAttendee);
