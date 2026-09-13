import { Component, t, useProps } from "@odoo/owl";

export class SlidesCourseJoinPopup extends Component {
    static template = "slide.course.join.popupContent";
    props = useProps({
        text: t.string().optional(),
        channelId: t.number().optional(),
        courseUrl: t.string().optional(),
        errorSignupAllowed: t.boolean().optional(),
        invitePreview: t.boolean().optional(),
        inviteHash: t.string().optional(),
        invitePartnerId: t.number().optional(),
        isPartnerWithoutUser: t.boolean().optional(),
        close: t.function(),
    });
}
