/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/components/chatter/chatter";
import { ChatterContainer } from "@mail/components/chatter_container/chatter_container";
var rpc = require('web.rpc');
const {onMounted} = owl;
import { FormRenderer } from '@web/views/form/form_renderer';
/** Patched FormRender for hiding the chatter. */
patch(Chatter.prototype, "parse", {
    async setup() {
     this._super(...arguments)
         this.orm = useService("orm");
         onMounted(async () => {
         try {
            // Fetch the list of model names from the configuration parameter
            const response = await this.orm.call("ir.config_parameter", "get_param", [
                "chatter_enable.model_ids", ])
            const model = await rpc.query({
                model: "ir.model",
                method: "search",
                args: [[["model", "=", this.chatter.threadModel]]],
                kwargs: { limit: 1 },})
            if (  response &&  response.includes(model[0])
            ) {
            this.el.classList.add("d-none")
            }
         }catch (error) {
            console.error("Error fetching configuration parameter:", error);
        }
         })
    },
});
