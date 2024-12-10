declare module "mock_models" {
    import { ChatbotScript as ChatbotScript2 } from "../chatbot_script";
    import { LivechatChannel as LivechatChannel2 } from "../im_livechat_channel";
    import { RatingRating as RatingRating2 } from "../rating_rating";
    import { ResLang as ResLang2 } from "../res_lang";

    export interface ChatbotScript extends ChatbotScript2 {}
    export interface LivechatChannel extends LivechatChannel2 {}
    export interface RatingRating extends RatingRating2 {}
    export interface ResLang extends ResLang2 {}

    export interface Models {
        "chatbot.script": ChatbotScript,
        "im_livechat.channel": LivechatChannel,
        "res.lang": ResLang,
    }
}
