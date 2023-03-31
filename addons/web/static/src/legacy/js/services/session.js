/** @odoo-module alias=web.session **/

import Session from "web.Session";

var session = new Session(undefined, undefined, {use_cors: false});
session.is_bound = session.session_bind();

export default session;
