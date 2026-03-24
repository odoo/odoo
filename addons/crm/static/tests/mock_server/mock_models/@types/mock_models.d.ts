declare module "mock_models" {
    export interface DiscussChannel {
        execute_command_lead: () => void;
        _types_allowing_create_lead: () => Array<string>;
    }
}
