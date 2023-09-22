/** @odoo-module **/

import { LinkDialog } from "@web_editor/js/wysiwyg/widgets/link_dialog";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import wUtils from "@website/js/utils";

patch(LinkDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.rpc = useService("rpc");
    },
    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    async start() {
        const options = {
            body: this.$link && this.$link[0].ownerDocument.body,
        };
        const result = await super.start(...arguments);
        wUtils.autocompleteWithPages(this.rpc.bind(this), this.$el.find('input[name="url"]'), options);
        return result;
    },
});
