declare module "models" {
    export interface Store {
        has_multi_website: boolean;
    }
    export interface DiscussChannel {
        requested_by_operator: boolean;
    }
    export interface Thread {
        livechat_visitor_id: WebsiteVisitor;
    }
    export interface WebsiteVisitor {
        discuss_channel_ids: DiscussChannel[];
        last_track_ids: WebsiteTrack[];
        track_count: number;
    }
}
