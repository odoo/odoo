import { useState } from "@odoo/owl";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { HRThread as Thread } from "@hr/components/mail/thread";

export class HRChatter extends Chatter {
    static template = "hr.Chatter";
    static components = {
        ...this.components,
        Thread,
    };

    setup() {
        super.setup();
        this.context = useState({
            version_id: this.props.record.data.version_id.id,
        });
    }

    _onWillUpdateProps(nextProps) {
        this.context.version_id = nextProps.record.data.version_id.id;
        super._onWillUpdateProps(nextProps);
    }
}
