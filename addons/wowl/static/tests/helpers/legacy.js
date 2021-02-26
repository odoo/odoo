odoo.define("wowl.test_legacy", async (require) => {
  const legacyExports = {};
  const legacyProm = new Promise(async (resolve) => {
    const session = require("web.session");
    await session.is_bound; // await for templates from server
    Object.assign(legacyExports, {
      makeTestEnvironment: require("web.test_env"),
      testUtils: require("web.test_utils"),
      basicFields: require("web.basic_fields"),
      Widget: require("web.Widget"),
      AbstractAction: require("web.AbstractAction"),
      AbstractController: require("web.AbstractController"),
      ListController: require("web.ListController"),
      core: require("web.core"),
      ReportClientAction: require("report.client_action"),
      AbstractView: require("web.AbstractView"),
      legacyViewRegistry: require("web.view_registry"),
      FormView: require("web.FormView"),
    });
    const CrashManager = require('web.CrashManager');
    CrashManager.disable();
    resolve(legacyExports);
  });
  function getLegacy() {
    return legacyExports;
  }

  return { legacyProm, getLegacy };
});
