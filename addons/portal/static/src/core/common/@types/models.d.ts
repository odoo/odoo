declare module "models" {
    export interface Message {
        is_internal: boolean|undefined;
        is_message_subtype_note: boolean|undefined;
        published_date_str: string|undefined;
    }
}
