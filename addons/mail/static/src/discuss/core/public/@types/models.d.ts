declare module "models" {
    export interface Store {
        companyName: string|undefined;
        discuss_public_thread: Thread;
        inPublicPage: boolean|undefined;
        isChannelTokenSecret: boolean|undefined;
        shouldDisplayWelcomeViewInitially: boolean|undefined;
    }
    export interface Thread {
        setActiveURL: () => void;
    }
}
