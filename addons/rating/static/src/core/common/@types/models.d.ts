declare module "models" {
    import { Rating as RatingClass } from "@rating/core/common/rating_model";

    export interface Rating extends RatingClass {}

    export interface Message {
        rating_id: Rating;
    }
    export interface Store {
        "rating.rating": StaticMailRecord<Rating, typeof RatingClass>;
    }
    export interface Thread {
        rating_stats: { avg: number, total: number, percent: Object<number, number>};
    }

    export interface Models {
        "rating.rating": Rating;
    }
}
