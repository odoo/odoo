declare module "models" {
    export interface DiscussChannel {
        appAsLivechats: DiscussApp;
        livechat_expertise_ids: LivechatExpertise[];
        livechat_status: "in_progress"|"waiting"|"need_help"|undefined;
        livechatStatusLabel: Readonly<string>;
        matchesSelfExpertise: Readonly<boolean>;
        shadowedBySelf: number;
        unpinOnThreadSwitch: boolean;
        updateLivechatStatus: (status: "in_progress"|"waiting"|"need_help") => void;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
    }
    export interface Thread {
        country_id: Country;
    }
}
