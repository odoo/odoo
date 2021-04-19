/** @odoo-module **/

import { useService } from "@web/core/hooks";
import { patch } from "@web/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { useListener } from "web.custom_hooks";
import { bus } from "web.core";

patch(WebClient.prototype, "web.service_provider_adapter", {
  setup() {
    // Effect Service
    const effect = useService("effect");
    useListener("show-effect", (ev) => {
      effect.create(ev.detail.message, ev.detail);
    });
    bus.on("show-effect", this, (payload) => {
      effect.create(payload.message, payload);
    });

    this._super(...arguments);
  },
});
