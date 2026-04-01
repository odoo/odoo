declare module "models" {
    import { Rating as RatingClass } from "@rating/core/common/rating_model";

    export interface Rating extends RatingClass {}

    export interface Message {
        rating_id: Rating;
    }
    export interface Store {
        "rating.rating": StaticMailRecord<Rating, typeof RatingClass>;
    }

    export interface Models {
        "rating.rating": Rating;
    }
}
