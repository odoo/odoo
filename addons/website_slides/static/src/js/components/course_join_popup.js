import { Component } from "@odoo/owl";

export class SlidesCourseJoinPopup extends Component {
    static template = "slide.course.join.popupContent";
    static props = {
        text: { type: String, optional: true },
        channelId: { type: Number, optional: true },
        courseUrl: { type: String, optional: true },
        errorSignupAllowed: { type: Boolean, optional: true },
        invitePreview: { type: Boolean, optional: true },
        inviteHash: { type: String, optional: true },
        invitePartnerId: { type: Number, optional: true },
        isPartnerWithoutUser: { type: Boolean, optional: true },
        close: Function,
    };
}
