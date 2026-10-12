import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { patch } from "@web/core/utils/patch";

patch(AvatarCard, {
    get allowedModels() {
        return [...super.allowedModels, "resource.resource"];
    },
});
/** @type {AvatarCard} */
const avatarCardPatch = {
    /** @override */
    get displayAvatar() {
        if (this.props.model === "resource.resource") {
            return Boolean(this.resource && this.resource.resource_type !== "material");
        }
        return super.displayAvatar;
    },
    /** @override */
    get name() {
        return this.resource?.name || super.name;
    },
    get resource() {
        if (this.props.model === "resource.resource") {
            return this.store["resource.resource"].get(this.props.id);
        }
        return undefined;
    },
    /** @override */
    get user() {
        if (this.props.model === "resource.resource") {
            return this.resource?.user_id;
        }
        return super.user;
    },
};
patch(AvatarCard.prototype, avatarCardPatch);
