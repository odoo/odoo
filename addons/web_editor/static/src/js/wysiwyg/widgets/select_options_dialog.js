odoo.define('wysiwyg.widgets.SelectOptionsDialog', function (require) {
'use strict';

const core = require('web.core');
const Dialog = require('wysiwyg.widgets.Dialog');

const _t = core._t;

const SelectOptionsDialog = Dialog.extend({
    template: 'wysiwyg.widgets.selectoptions',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/wysiwyg.xml']
    ),
    events: _.extend({}, Dialog.prototype.events, {
        'change textarea.o_select_options': '_onChangeOptions',
    }),

    /**
     * @constructor
     */
    init: function (parent, options, select) {
        this._super(parent, _.extend({}, {
            title: _t("Edit your options"),
            save_text: _t("Add"),
        }, options || {}));
        this.select = select;
        if (this.select) {
            this.selectOptions = [...this.select.querySelectorAll('option')].map(option => {
                return $(option).text();
            });
        } else {
            this.selectOptions = [];
        }
    },
    /**
     * @override
     */
    save: function () {
        const $options = this.selectOptions.map(option => $(`<option>${option}</option>`));
        const $select = $('<select contenteditable="false"/>');
        $select.append(...$options);
        this.final_data = $select[0];
        return this._super(...arguments);
    },
    selectOptionsText: function () {
        return this.selectOptions.join('\n');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChangeOptions: function (ev) {
        this.selectOptions = $(ev.target).val().split('\n').map(option => option.trim());
    },
});

return SelectOptionsDialog;
});
