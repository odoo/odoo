odoo.define('mass_mailing.wysiwyg', function (require) {
'use strict';

var Wysiwyg = require('web_editor.wysiwyg');
var MassMailingSnippetsMenu = require('mass_mailing.snippets.editor');

const MassMailingWysiwyg = Wysiwyg.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    start: async function () {
        const res = await this._super(...arguments);
        // Prevent selection change outside of snippets.
        this.$editable.on('mousedown', e => {
            if ($(e.target).is('.o_editable:empty') || e.target.querySelector('.o_editable')) {
                e.preventDefault();
            }
        });
        return res;
    },

    /**
     * @override
     */
     setValue: function (currentValue) {
        const initialDropZone = this.$editable[0].querySelector('.o_mail_wrapper_td');
        const parsedHtml = new DOMParser().parseFromString(currentValue, "text/html");
        if (initialDropZone && !parsedHtml.querySelector('.o_mail_wrapper_td')) {
            initialDropZone.replaceChildren(...parsedHtml.body.childNodes);
        } else {
            this._super(...arguments);
        }
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _createSnippetsMenuInstance: function (options={}) {
        return new MassMailingSnippetsMenu(this, Object.assign({
            wysiwyg: this,
            selectorEditableArea: '.o_editable',
        }, options));
    },
});

return MassMailingWysiwyg;

});
