odoo.define('website.tour.public_user_editor_dep_widget', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const wysiwygLoader = require('web_editor.loader');

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
});

odoo.define('website.tour.public_user_editor', function (require) {
'use strict';

const tour = require('web_tour.tour');

tour.register('public_user_editor', {
    test: true,
}, [{
    trigger: '.note-editable',
    run: function () {}, // Simple check
}]);
});
