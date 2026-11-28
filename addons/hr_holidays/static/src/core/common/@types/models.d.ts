declare module "models" {
    export interface HrEmployee {
        leave_back_datetime: import("luxon").DateTime;
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
