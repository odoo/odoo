declare module "models" {
    export interface Persona {
        livechat_languages: String[],
        livechat_expertise: String[],
    }
    export interface Thread {
        livechat_operator_id: Persona,
    }
}
