declare module "models" {
    export interface Store {
        companyName: string|undefined;
        inPublicPage: boolean|undefined;
        is_welcome_page_displayed: boolean|undefined;
        isChannelTokenSecret: boolean|undefined;
    }
    export interface Thread {
        setActiveURL: () => void;
    }
}
