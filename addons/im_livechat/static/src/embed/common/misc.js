import { session } from "@web/session";

export const GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";

export function canLoadLivechat() {
    const sessionData = session.livechatData ?? {};
    return "can_load_livechat" in sessionData
        ? sessionData.can_load_livechat
        : sessionData.isAvailable;
}
