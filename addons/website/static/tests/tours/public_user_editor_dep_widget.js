/** @odoo-module **/

import publicWidget from "web.public.widget";
import wysiwygLoader from "web_editor.loader";

publicWidget.registry['public_user_editor_test'] = publicWidget.Widget.extend({
    selector: 'textarea.o_public_user_editor_test_textarea',

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        await wysiwygLoader.loadFromTextarea(this, this.el, {});
    },
});
