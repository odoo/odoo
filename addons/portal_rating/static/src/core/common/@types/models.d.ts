declare module "models" {
    export interface Rating {
        publisher_comment: string|undefined;
        publisher_datetime: import("luxon").DateTime;
        publisher_id: ResPartner;
    }
    export interface ResPartner {
        is_user_publisher: boolean|undefined;
    }
}
