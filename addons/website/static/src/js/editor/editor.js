/** @odoo-module **/

import { LinkDialog } from "@web_editor/js/wysiwyg/widgets/link_dialog";
import { patch } from "@web/core/utils/patch";
import wUtils from "@website/js/utils";
import { useEffect } from '@odoo/owl';

patch(LinkDialog.prototype, {
    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    setup() {
        super.setup();
        useEffect(($link, container) => {
            const input = container?.querySelector(`input[name="url"]`);
            if (!input) {
                return;
            }
            const options = {
                body: $link && $link[0].ownerDocument.body,
                urlChosen: () => this.__onURLInput(),
            };
            const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(input, options);
            return () => unmountAutocompleteWithPages();
        }, () => [this.$link, this.linkComponentWrapperRef.el]);
    }
});
