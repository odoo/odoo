declare module "models" {
    export interface DiscussChannel {
        appAsLivechats: DiscussApp;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
    }
    export interface Thread {
        country_id: Country;
<<<<<<< 74f09c9148b80fbd5202582ef90a0ced629afd03
||||||| 2217d5220640531828eb5b2ae7a9d41ba9c97e78
        livechat_channel_id: LivechatChannel;
        livechat_expertise_ids: LivechatExpertise[];
        livechat_status: "in_progress"|"waiting"|"need_help"|undefined;
        matchesSelfExpertise: Readonly<boolean>;
        shadowedBySelf: number;
        wasLookingForHelp: boolean;
=======
        livechat_channel_id: LivechatChannel;
        livechat_expertise_ids: LivechatExpertise[];
        livechat_status: "in_progress"|"waiting"|"need_help"|undefined;
        matchesSelfExpertise: Readonly<boolean>;
        shadowedBySelf: number;
>>>>>>> 4f65087f28f2ed781c78a11b2fb8c4e68d62a379
    }
}
