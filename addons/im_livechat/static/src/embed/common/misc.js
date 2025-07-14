import { session } from "@web/session";

export function isValidEmail(val) {
    // http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
    const re =
        /^(([^<>()[\].,;:\s@"]+(\.[^<>()[\].,;:\s@"]+)*)|(".+"))@(([^<>()[\].,;:\s@"]+\.)+[^<>()[\].,;:\s@"]{2,})$/i;
    return re.test(val);
}

export function canLoadLivechat() {
    const sessionData = session.livechatData ?? {};
    return "can_load_livechat" in sessionData
        ? sessionData.can_load_livechat
        : sessionData.isAvailable;
}
