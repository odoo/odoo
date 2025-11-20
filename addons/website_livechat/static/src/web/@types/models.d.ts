declare module "models" {
    export interface WebsiteVisitor {
        discuss_channel_ids: DiscussChannel[];
        last_track_ids: WebsiteTrack[];
        pageVisitHistoryText: Readonly<string>;
    }
}
