declare module "@web/services/user" {
    import { EventBus } from "@odoo/owl";
    import { Context } from "@web/core/context";

    export interface UserCompany {
        id: number;
        name: string;
        sequence: number;
        child_ids: number[];
        parent_id: number | false;
        currency_id?: number | false;
    }

    export interface User {
        name: string;
        login: string;
        isAdmin: boolean;
        isSystem: boolean;
        isInternalUser: boolean;
        partnerId: number;
        homeActionId: number | false;
        showEffect: boolean;
        userId: number;
        writeDate: string;
        readonly context: Context & { uid: number };
        readonly lang: string;
        readonly tz: string;
        readonly settings: Record<string, any>;
        defaultCompany: UserCompany | undefined;
        allowedCompanies: UserCompany[];
        allowedCompaniesWithAncestors: UserCompany[];
        readonly activeCompanies: UserCompany[];
        readonly activeCompany: UserCompany | undefined;
        updateContext(update: Partial<Context>): void;
        hasGroup(group: string): Promise<boolean>;
        checkAccessRight(
            model: string,
            operation: string,
            ids?: number | number[]
        ): Promise<boolean>;
        setUserSettings(key: string, value: any): Promise<void>;
        updateUserSettings(key: string, value: any): void;
        activateCompanies(
            companyIds: number[],
            options?: {
                includeChildCompanies?: boolean;
                reload?: boolean;
            }
        ): Promise<void>;
    }

    export const user: User;
    export const userBus: EventBus;
    export function _makeUser(session: Record<string, any>): User;
    export function getLastConnectedUsers(): any[];
    export function setLastConnectedUsers(users: any[]): void;
}
