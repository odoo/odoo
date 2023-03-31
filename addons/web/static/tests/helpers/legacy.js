odoo.define("web.test_legacy", async (require) => {
    require("web.SessionOverrideForTests");
    require("web.test_utils");
    const session = require("web.session");
    await session.is_bound; // await for templates from server

    return { legacyProm: session.is_bound };
});
