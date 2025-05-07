import { Component } from "@odoo/owl";
import { useDomState } from "@html_builder/core/utils";
import { useOperation } from "@html_builder/core/operation_plugin";

export class AvatarsHeaderMiddleButtons extends Component {
    static template = "website.AvatarsHeaderMiddleButtons";
    static props = {
        addAvatar: Function,
        removeAvatar: Function,
    };

    setup() {
        this.callOperation = useOperation();
        this.state = useDomState((editingElement) => {
            const avatarEls = editingElement.querySelectorAll(".s_avatars_wrapper .o_avatar");
            return {
                disableRemoveButton: avatarEls.length <= 1,
            };
        });
    }

    addAvatar() {
        this.callOperation(() => {
            this.props.addAvatar(this.env.getEditingElement());
        });
    }

    removeAvatar() {
        this.callOperation(() => {
            this.props.removeAvatar(this.env.getEditingElement());
        });
    }
}
