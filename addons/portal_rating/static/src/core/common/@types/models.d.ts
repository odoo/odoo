declare module "models" {
    export interface Message {
        rating_stats: Object|undefined;
        rating_value: number|null|undefined;
    }
    export interface Rating {
        publisher_avatar: string|undefined;
        publisher_comment: string|undefined;
        publisher_datetime: string|undefined;
        publisher_id: number|false|undefined;
        publisher_name: string|undefined;
    }
    export interface ResPartner {
        is_user_publisher: boolean|undefined;
    }
}
