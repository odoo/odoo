odoo.define("web.session", function (require) {
    const Session = require("web.Session");
    const { serverUrl } = require("@im_livechat/livechat_data");

    return new Session(undefined, serverUrl, { use_cors: true });
});
