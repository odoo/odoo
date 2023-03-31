/** @odoo-module alias=web.session **/

import Session from "web.Session";
import { serverUrl } from "@im_livechat/livechat_data";

export default new Session(undefined, serverUrl, { use_cors: true });
