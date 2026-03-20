import { useOpenChat } from "@mail/core/web/open_chat_hook";

import { patch } from "@web/core/utils/patch";
import { PropertyValue } from "@web/views/fields/properties/property_value";

/**
 * Allow to open the chatter of the user when we click on the avatar of a Many2one
 * property (like we do for many2one_avatar_user widget).
 */
patch(PropertyValue.prototype, {
    setup() {
        super.setup();

        if (this.env.services["mail.store"]) {
            // work only for the res.users model
            this.openChat = useOpenChat("res.users");
        }
    },

    get propertyValue() {
        const value = super.propertyValue;
        if (this.props.type === "many2many") {
            return value.map((tag) => {
                if (this.openChat && this.props.comodel === "res.users") {
                    tag.props.onAvatarClick = () => {
                        this.openChat(tag.id);
                    };
                }
                return tag;
            });
        }
        return value;
    },

    _onAvatarClicked() {
        if (this.openChat && this.showAvatar && this.props.comodel === "res.users") {
            this.openChat(this.props.value.id);
        }
    },
});
