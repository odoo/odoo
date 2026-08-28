import { Component, useProps, t } from "@odoo/owl";
import { useDomState } from "@html_builder/core/utils";
import { useOperation } from "@html_builder/core/operation_plugin";

export class AvatarsHeaderMiddleButtons extends Component {
    static template = "website.AvatarsHeaderMiddleButtons";
    props = useProps({
        addAvatar: t.function(),
        removeAvatar: t.function(),
    });

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
        if (!this.state.disableRemoveButton) {
            this.callOperation(() => {
                this.props.removeAvatar(this.env.getEditingElement());
            });
        }
    }
}
