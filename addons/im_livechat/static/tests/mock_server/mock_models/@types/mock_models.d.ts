declare module "mock_models" {
    import { LivechatChannel as LivechatChannel2 } from "../im_livechat_channel";
    import { RatingRating as RatingRating2 } from "../rating_rating";

    export interface LivechatChannel extends LivechatChannel2 {}
    export interface RatingRating extends RatingRating2 {}

    export interface Models {
        "im_livechat.channel": LivechatChannel,
    }
}
