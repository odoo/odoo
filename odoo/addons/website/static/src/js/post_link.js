/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import wUtils from "@website/js/utils";

publicWidget.registry.postLink = publicWidget.Widget.extend({
    selector: '.post_link',
    events: {
        'click': '_onClickPost',
    },

    /**
     * @override
     */
    start() {
        // Allows the link to be interacted with only when Javascript is loaded.
        this.el.classList.add('o_post_link_js_loaded');
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.el.classList.remove('o_post_link_js_loaded');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickPost: function (ev) {
        ev.preventDefault();
        const url = this.el.dataset.post || this.el.href;
        let data = {};
        for (let [key, value] of Object.entries(this.el.dataset)) {
            if (key.startsWith('post_')) {
                data[key.slice(5)] = value;
            }
        }
        wUtils.sendRequest(url, data);
    },
});
