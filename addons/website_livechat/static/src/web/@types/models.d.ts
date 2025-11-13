declare module "models" {
    export interface WebsiteVisitor {
        discuss_channel_ids: Thread[];
        last_track_ids: WebsiteTrack[];
        pageVisitHistoryText: Readonly<string>;
    }
}
