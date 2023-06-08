/** @odoo-module **/

import { LinkDialog } from "@web_editor/js/wysiwyg/widgets/link_dialog";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import wUtils from 'website.utils';

patch(LinkDialog.prototype, "editor.js", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
    },
    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    start: async function () {
        const options = {
            body: this.$link && this.$link[0].ownerDocument.body,
        };
        const result = await this._super.apply(this, arguments);
        // wUtils.autocompleteWithPages rely on a widget that has a _rpc and
        // trigger_up method.
        const fakeWidget = {
            _rpc: ({ route, params }) => this.rpc(route, params),
            trigger_up: () => {},
        };
        wUtils.autocompleteWithPages(fakeWidget, this.$el.find('input[name="url"]'), options);
        return result;
    },
});
