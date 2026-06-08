declare module "models" {
    export interface ScheduledMessage {
        cancel: () => Promise<void>;
        deletable: Readonly<unknown>;
        edit: () => Promise<undefined|Promise<unknown>>;
        editable: Readonly<unknown>;
        isSelfAuthored: Readonly<unknown>;
        isSubjectThreadName: Readonly<boolean>;
        notifyAlreadySent: () => void;
        send: () => Promise<void>;
        textContent: string|unknown;
    }
}
