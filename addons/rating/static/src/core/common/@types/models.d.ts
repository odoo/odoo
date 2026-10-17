declare module "models" {
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { Rating as RatingClass } from "@rating/core/common/rating_model";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Rating extends RatingClass {}

    export interface Message extends Patch<MessageClass, typeof import("@rating/core/common/message_model_patch").messagePatch> {
        rating_id: Rating;
    }
    export interface Store {
        "rating.rating": StaticMailRecord<Rating, typeof RatingClass>;
    }
    export interface Thread extends Patch<ThreadClass, typeof import("@rating/core/common/thread_model_patch").threadPatch> {
        rating_avg: number|undefined;
        rating_count: number|undefined;
        rating_stats: { avg: number, total: number, percent: Object<number, number>}|undefined;
    }
    export interface Models {
        "rating.rating": Rating;
    }
}
