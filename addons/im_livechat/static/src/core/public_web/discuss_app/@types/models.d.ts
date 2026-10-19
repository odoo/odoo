declare module "models" {
    export interface DiscussApp {
        isLivechatInfoPanelOpenByDefault: boolean;
        livechats: DiscussChannel[];
    }
}
