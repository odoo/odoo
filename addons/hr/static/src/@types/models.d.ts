declare module "models" {
    export interface Store {
        employees: {[key: number]: {id: number, user_id: number, hasCheckedUser: boolean}};
    }
}
