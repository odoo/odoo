declare module "models" {
    export interface HrEmployee {
        leave_date_to: import("luxon").DateTime;
        outOfOfficeDateEndText: Readonly<string>;
    }
    export interface ResPartner {
        outOfOfficeDateEndText: Readonly<string>;
    }
    export interface ResUsers {
        outOfOfficeDateEndText: Readonly<string>;
    }
}
