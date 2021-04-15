/** @odoo-module **/

import { useService } from "@web/core/hooks";
import { patch } from "@web/utils/patch";
import { WebClient } from "@web/webclient/webclient";
const { useListener } = require("web.custom_hooks");
const core = require("web.core");

patch(WebClient.prototype, "web.service_provider_adapter", {
  setup() {
    // Effect Service
    const effect = useService("effect");
    useListener("show-effect", (ev) => {
      effect.create(ev.detail.message, ev.detail);
    });
    core.bus.on("show-effect", this, (payload) => {
      effect.create(payload.message, payload);
    });

    this._super(...arguments);
  },
});
