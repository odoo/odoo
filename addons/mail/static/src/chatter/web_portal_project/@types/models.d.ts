declare module "models" {
    export interface Thread {
        fetchThreadData: (requestList: string[]) => Promise<void>;
        fullComposerCloseRequestList: Readonly<string[]>;
    }
}
