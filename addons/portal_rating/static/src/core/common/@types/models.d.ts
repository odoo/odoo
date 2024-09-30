declare module "models" {
    export interface Rating {
        publisher_comment: string;
        publisher_datetime: import("luxon").DateTime;
        publisher_id: ResPartner;
    }
}
