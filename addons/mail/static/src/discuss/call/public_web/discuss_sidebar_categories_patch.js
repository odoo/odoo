import { DiscussSidebarCallParticipants } from "@mail/discuss/call/public_web/discuss_sidebar_call_participants";
import { DiscussSidebarCategories } from "@mail/discuss/core/public_web/discuss_sidebar_categories";

DiscussSidebarCategories.components = Object.assign(DiscussSidebarCategories.components || {}, {
    DiscussSidebarCallParticipants,
});
