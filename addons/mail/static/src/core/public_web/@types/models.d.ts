declare module "models" {
    import { DiscussApp as DiscussAppClass } from "@mail/core/public_web/discuss_app_model";

    export interface DiscussApp extends DiscussAppClass { }
    export interface Store {
        DiscussApp: DiscussApp,
        discuss: DiscussApp,
        action_discuss_id: number,
    }
    export interface Thread {
        setAsDiscussThread: (pushState: boolean) => void,
        unpin: () => Promise<void>,
        askLeaveConfirmation: (body: string) => void,
        leaveChannel: () => Promise<void>,
    }
    export interface Models {
        "DiscussApp": DiscussApp,
    }
}
