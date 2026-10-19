import { useService } from "@web/core/utils/hooks";
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
            this.store = useService("mail.store");
        }
    },

    get propertyValue() {
        const value = super.propertyValue;
        if (this.props.type === "many2many") {
            return value.map((tag) => {
                if (this.store && this.props.comodel === "res.users") {
                    tag.props.onAvatarClick = () => {
                        this.store.openChat({ userId: tag.id });
                    };
                }
                return tag;
            });
        }
        return value;
    },

    _onAvatarClicked() {
        if (this.store && this.showAvatar && this.props.comodel === "res.users") {
            this.store.openChat({ userId: this.props.value.id });
        }
    },
});
