const { Component } = owl;

odoo.define("root.widget", function (require) {
  require("web.legacySetup");
  const { ComponentAdapter } = require("web.OwlCompatibility");
  return new ComponentAdapter(null, { Component }); // for its method _trigger_up
});
