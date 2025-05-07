import { useDomState } from "@html_builder/core/utils";
import { useOperation } from "@html_builder/core/operation_plugin";
import { Component } from "@odoo/owl";

export class AvatarsHeaderMiddleButtons extends Component {
    static template = "website.AvatarsHeaderMiddleButtons";
    static props = {
        addAvatar: Function,
        removeAvatar: Function,
    };

    setup() {
        this.state = useDomState((editingElement) => {
            const containerEl = editingElement.querySelector('.s_avatars_rules_collector');
            return {
                avatarEls: containerEl ? containerEl.querySelectorAll('.o_avatar') : [],
            };
        });

        this.callOperation = useOperation();
    }

    addAvatar() {
        this.callOperation(async () => {
            await this.props.addAvatar(this.env.getEditingElement());
        });
    }

    removeAvatar() {
        this.callOperation(() => {
            this.props.removeAvatar(this.env.getEditingElement());
        });
    }
}
