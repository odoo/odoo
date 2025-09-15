declare module "models" {
    export interface Composer {
        portalComment: boolean;
    }
    export interface Thread {
        hasReadAccess: boolean|undefined;
    }
}
