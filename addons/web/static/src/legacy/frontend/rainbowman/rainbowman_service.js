/** @odoo-module **/
import RainbowMan from "web.RainbowMan";
import { bus } from "web.core";

/**
 * This is used when an effect is demanded but the webclient
 * isn't a parent of the current context. Like in the tour manager in website. 
 */
bus.on("show-effect", this, (payload) => {
  new RainbowMan({ message: payload.message, fadeout: payload.fadeout }).appendTo(
    document.getElementsByTagName("body")[0]
  );
});
