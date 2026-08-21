import { Component, types, useProps } from "@odoo/owl";

/** Tells how long ago the invitation of a channel member who has not joined yet was last sent. */
export class InvitationSentDate extends Component {
    static template = "discuss.InvitationSentDate";

    setup() {
        super.setup();
        this.props = useProps({
            datetime: types.signal(types.instanceOf(luxon.DateTime)),
        });
    }

    get relativeTime() {
        return this.props.datetime().toRelative({ style: "narrow" });
    }
}
