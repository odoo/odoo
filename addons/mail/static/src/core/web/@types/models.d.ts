import { Persona } from "@mail/core/common/persona_model";
import { DateTime } from "luxon";

declare module "models" {
    export interface Activity {
        active: boolean,
        activity_category: string,
        activity_type_id: [number, string],
        activity_decoration: string|false,
        attachment_ids: Object[],
        can_write: boolean,
        chaining_type: 'suggest'|'trigger',
        create_date: DateTime,
        create_uid: [number, string],
        date_deadline: DateTime,
        date_done: DateTime,
        display_name: string,
        has_recommended_activities: boolean,
        feedback: string,
        icon: string,
        mail_template_ids: Object[],
        note: string,
        persona: Persona,
        previous_activity_type_id: number|false,
        recommended_activity_type_id: number|false,
        res_model: string,
        res_model_id: [number, string],
        res_id: number,
        res_name: string,
        request_partner_id: number|false,
        state: 'overdue'|'planned'|'today',
        summary: string,
        user_id: [number, string],
        write_date: string,
        write_uid: [number, string],
    }
    export interface Discuss  {
        inbox: Thread,
        stared: Thread,
        history: Thread,
    }
    export interface Store {
        activityCounter: number,
        activity_counter_bus_id: number,
        activityGroups: Object[],
    }
    export interface Thread {
        recipients: Follower[],
    }
}
