import { Follow } from "./follow";
import { registry } from "@web/core/registry";

const FollowEdit = I => class extends I {
    dynamicContent = {};
};

registry
    .category("public.interactions.edit")
    .add("website_mail.follow", {
        Interaction: Follow,
        mixin: FollowEdit,
    });
