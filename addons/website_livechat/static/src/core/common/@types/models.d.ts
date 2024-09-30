declare module "models" {
    export interface Thread {
        livechat_visitor_id: WebsiteVisitor;
    }
    export interface WebsiteVisitor {
        discuss_channel_ids: DiscussChannel[];
        last_track_ids: WebsiteTrack[];
    }
}
