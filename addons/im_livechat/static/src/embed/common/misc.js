import { session } from "@web/session";

export function canLoadLivechat() {
    const sessionData = session.livechatData ?? {};
    return "can_load_livechat" in sessionData
        ? sessionData.can_load_livechat
        : sessionData.isAvailable;
}
