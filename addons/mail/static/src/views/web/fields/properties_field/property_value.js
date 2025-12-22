import { useOpenChat } from "@mail/core/web/open_chat_hook";

import { TagsList } from "@web/core/tags_list/tags_list";
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

    _onAvatarClicked() {
        if (this.openChat && this.showAvatar && this.props.comodel === "res.users") {
            this.openChat(this.props.value[0]);
        }
    },
});

/**
 * Allow to open the chatter of the user when we click on the avatar of a Many2many
 * property (like we do for many2many_avatar_user widget).
 */
export class Many2manyPropertiesTagsList extends TagsList {
    static template = "mail.Many2manyPropertiesTagsList";

    setup() {
        super.setup();
        if (this.env.services["mail.store"]) {
            this.openChat = useOpenChat("res.users");
        }
    }

    _onAvatarClicked(tagIndex) {
        const tag = this.props.tags[tagIndex];
        if (this.openChat && tag.comodel === "res.users") {
            this.openChat(tag.id);
        }
    }
}

PropertyValue.components = {
    ...PropertyValue.components,
    TagsList: Many2manyPropertiesTagsList,
};
