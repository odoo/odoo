declare module "models" {
    export interface LivechatChannel {
        join: (param0: { notify: boolean }) => Promise<void>;
        joinTitle: Readonly<string>;
        leave: (param0: { notify: boolean }) => Promise<void>;
        leaveTitle: Readonly<string>;
    }
    export interface Store {
        goToOldestUnreadLivechatThread: () => boolean;
        has_access_livechat: boolean;
        livechatChannels: ReturnType<Store['makeCachedFetchData']>;
        livechatStatusButtons: Readonly<object[]>;
    }
    export interface Thread {
        hasFetchedLivechatSessionData: boolean;
        livechat_expertise_ids: LivechatExpertise[];
        livechat_note: ReturnType<import("@odoo/owl").markup>|string;
        livechat_outcome: unknown;
        livechat_status: unknown;
        livechatNoteText: unknown;
        livechatStatusLabel: Readonly<string>;
        updateLivechatStatus: (status: unknown) => void;
    }
}
