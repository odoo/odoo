declare module "models" {
    export interface DiscussChannel {
        requested_by_operator: boolean;
    }
    export interface Thread {
        livechat_visitor_id: WebsiteVisitor;
    }
    export interface WebsiteVisitor {
        last_track_ids: WebsiteTrack[];
    }
}
