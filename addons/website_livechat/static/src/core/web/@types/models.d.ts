declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";
    import { WebsiteVisitor as WebsiteVisitorClass } from "@website/mail/core/common/website_visitor_model";

    export interface ChannelMember extends Patch<ChannelMemberClass, typeof import("@website_livechat/core/web/channel_member_model_patch").channelMemberPatch> {}
    export interface WebsiteVisitor extends Patch<WebsiteVisitorClass, typeof import("@website_livechat/core/web/website_visitor_model_patch").websiteVisitorPatch> {}
}
