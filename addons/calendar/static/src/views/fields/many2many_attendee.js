import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import {
    Many2ManyTagsAvatarField,
    many2ManyTagsAvatarField,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { ConnectionLostError } from "@web/core/network/rpc";

const ICON_BY_STATUS = {
    accepted: "fa-check",
    declined: "fa-times",
    tentative: "fa-question",
};

export class AttendeeTag extends Component {
    static template = "calendar.AttendeeTag";
    static props = ["imageUrl", "isUnavailable?", "noEmail?", "onDelete?", "status?", "text", "tooltip"];

    get statusIcon() {
        return ICON_BY_STATUS[this.props.status];
    }
}

export class Many2ManyAttendee extends Many2ManyTagsAvatarField {
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
    ...many2ManyTagsAvatarField,
    component: Many2ManyAttendee,
    additionalClasses: ["o_field_many2many_tags_avatar", "w-100"],
};

registry.category("fields").add("many2manyattendee", many2ManyAttendee);
