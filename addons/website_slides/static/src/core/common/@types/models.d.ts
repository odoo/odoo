declare module "models" {
    export interface Activity {
        request_partner_id: ResPartner;
    }
    export interface Thread {
        comments_count: number | undefined;
    }
}
