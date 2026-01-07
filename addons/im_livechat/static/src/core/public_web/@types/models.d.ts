declare module "models" {
    export interface DiscussChannel {
        appAsLivechats: DiscussApp;
        livechat_expertise_ids: LivechatExpertise[];
        livechat_lang_id: ResLang;
        livechat_status: "in_progress"|"need_help"|undefined;
        livechatStatusLabel: Readonly<string>;
        matchesSelfExpertise: Readonly<boolean>;
        shadowedBySelf: number;
        unpinOnThreadSwitch: boolean;
        updateLivechatStatus: (status: "in_progress"|"need_help") => void;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
    }
    export interface Thread {
        country_id: Country;
    }
}
