declare module "models" {
    export interface HrEmployee {
        leave_date_to: import("luxon").DateTime;
    }
    export interface ResUsers {
        leave_date_to: string;
    }
}
