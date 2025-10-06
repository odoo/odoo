declare module "models" {
    export interface WebsiteVisitor {
        discuss_channel_ids: Thread[];
        page_visit_history: Array<[string, string]>;
        pageVisitHistoryText: Readonly<string>;
    }
}
