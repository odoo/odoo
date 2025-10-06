declare module "models" {
    export interface Composer {
        portalComment: boolean;
    }
    export interface DiscussChannel {
        hasReadAccess: boolean|undefined;
    }
    export interface Thread {
        hasReadAccess: boolean|undefined;
    }
}
