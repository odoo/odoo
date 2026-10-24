declare module "models" {
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";
    import { WebsiteVisitor as WebsiteVisitorClass } from "@website/mail/core/common/website_visitor_model";

    export interface DiscussChannel extends Patch<DiscussChannelClass, typeof import("@website_livechat/core/common/discuss_channel_model_patch").discussChannelPatch, "hasWelcomeMessage"> {
        requested_by_operator: boolean;
    }
    export interface Thread extends Patch<ThreadClass, typeof import("@website_livechat/core/common/thread_model_patch").threadPatch> {
        livechat_visitor_id: WebsiteVisitor;
    }
    export interface WebsiteVisitor extends Patch<WebsiteVisitorClass, typeof import("@website_livechat/core/common/website_visitor_model_patch").websiteVisitorPatch> {
        discuss_channel_ids: DiscussChannel[];
        last_track_ids: WebsiteTrack[];
    }
}
