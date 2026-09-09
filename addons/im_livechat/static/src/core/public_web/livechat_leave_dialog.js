import { discussComponentRegistry } from "@mail/core/common/discuss_component_registry";
import { Component, t, useProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class LivechatLeaveDialog extends Component {
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        channel: t.object(),
        onConfirm: t.function(),
    });
    static template = "im_livechat.LivechatLeaveDialog";

    get messageComponent() {
        return discussComponentRegistry.get("Message");
    }

    get title() {
        return _t(
            "Closing this will end the live chat with %(channel_name)s. Are you sure you want to proceed?",
            { channel_name: this.props.channel.displayName }
        );
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}
