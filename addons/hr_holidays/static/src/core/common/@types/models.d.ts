declare module "models" {
    export interface HrEmployee {
        isBackToday: Readonly<boolean>;
        isOnLeave: Readonly<boolean>;
        leave_datetime_to: import("luxon").DateTime;
        outOfOfficeDateEndText: Readonly<string>;
    }
    export interface ResPartner {
        outOfOfficeDateEndText: Readonly<string>;
    }
    export interface ResUsers {
        outOfOfficeDateEndText: Readonly<string>;
    }
}
