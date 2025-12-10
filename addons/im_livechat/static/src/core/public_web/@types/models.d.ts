declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory;
        lastThread: Thread;
        livechatLookingForHelpCategory: DiscussAppCategory;
        livechats: Thread[];
    }
    export interface DiscussAppCategory {
        livechat_channel_id: LivechatChannel;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
        threads: Thread[];
    }
    export interface Thread {
        appAsLivechats: DiscussApp;
        country_id: Country;
        livechat_channel_id: LivechatChannel;
        livechat_expertise_ids: LivechatExpertise[];
        livechat_status: "in_progress"|"waiting"|"need_help"|undefined;
        matchesSelfExpertise: Readonly<boolean>;
        shadowedBySelf: number;
    }
}
