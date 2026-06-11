import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { useProps } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class LivechatButtonPreview extends LivechatButton {
    props = useProps(standardWidgetProps);

    setup() {
        this.state = { animateNotification: true };
    }

    get isShown() {
        return true;
    }

    get livechatService() {
        return { options: this.props.record.data };
    }

    get store() {
        return {
            livechat_rule: this.props.record.data.button_text && {
                action: "display_button_and_text",
            },
        };
    }
}
