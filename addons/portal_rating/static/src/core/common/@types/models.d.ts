declare module "models" {
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { Rating as RatingClass } from "@rating/core/common/rating_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";

    export interface Message extends Patch<MessageClass, typeof import("@portal_rating/core/common/message_model_patch").messagePatch> {
        rating_stats: Object|undefined;
        rating_value: number|null|undefined;
    }
    export interface Rating extends Patch<RatingClass, typeof import("@portal_rating/core/common/rating_model_patch").ratingPatch> {
        publisher_avatar: string|undefined;
        publisher_comment: string|undefined;
        publisher_datetime: string|undefined;
        publisher_id: number|false|undefined;
        publisher_name: string|undefined;
    }
    export interface ResPartner extends Patch<ResPartnerClass, typeof import("@portal_rating/core/common/res_partner_model_patch").resPartnerPatch> {
        is_user_publisher: boolean|undefined;
    }
}
