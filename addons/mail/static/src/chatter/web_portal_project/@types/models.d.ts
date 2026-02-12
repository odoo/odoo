declare module "models" {
    export interface Thread {
        fetchThreadData: (requestList: string[], param0: { messageFetchRouteParams: MessageRouteParams }) => Promise<void>;
    }
}
