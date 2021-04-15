/** @odoo-module **/
const RainbowMan = require("web.RainbowMan");
const core = require("web.core");

core.bus.on("show-effect", this, (payload) => {
  new RainbowMan({ message: payload.message, fadeout: payload.fadeout }).appendTo(
    document.getElementsByTagName("body")[0]
  );
});
