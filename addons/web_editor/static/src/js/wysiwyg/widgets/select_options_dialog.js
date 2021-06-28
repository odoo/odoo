odoo.define('wysiwyg.widgets.SelectOptionsDialog', function (require) {
'use strict';

const core = require('web.core');
const Dialog = require('wysiwyg.widgets.Dialog');

const _t = core._t;
const qweb = core.qweb;

let optionId = 1;
const SelectOptionsDialog = Dialog.extend({
    template: 'wysiwyg.widgets.selectoptions',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/wysiwyg.xml']
    ),
    events: _.extend({}, Dialog.prototype.events, {
        'click a.js_add_option': '_onAddOptionButtonClick',
        'click button.js_delete_option': '_onDeleteOptionButtonClick',
        'click button.js_edit_option': '_onEditOptionButtonClick',
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
            let id = 0;
            this.selectOptions = [...this.select.querySelectorAll('option')].map(option => {
                id++;
                return {
                    id,
                    label: $(option).text(),
                    value: option.getAttribute('value'),
                };
            });
        } else {
            this.selectOptions = [];
        }
    },
    /**
     * @override
     */
    start: function () {
        var r = this._super.apply(this, arguments);
        this.$('.oe_selectoption_editor').sortable({
            listType: 'ul',
            handle: 'div',
            items: 'li',
            toleranceElement: '> div',
            forcePlaceholderSize: true,
            opacity: 0.6,
            placeholder: 'oe_option_placeholder',
            tolerance: 'pointer',
            attribute: 'data-option-id',
            update: ev => {
                // Reorder the options.
                const ids = $(ev.target).find('[data-option-id]').toArray().map(option => +option.dataset.optionId);
                this.selectOptions = ids.map(id => this.selectOptions.find(option => option.id === id));
                this._updatePreview();
            }
        });
        return r;
    },
    /**
     * @override
     */
    save: function () {
        const $options = this.selectOptions.map(option => $(`<option value=${option.value}>${option.label}</option>`));
        const $select = $('<select contenteditable="false"/>');
        $select.append(...$options);
        this.final_data = $select[0];
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Redraw the preview of the Select element based on `selectOptions`.
     *
     * @private
     */
    _updatePreview: function () {
        this.$('#o_selectoptions_dialog_preview').empty().append(
            $(`<select>${this.selectOptions.map(option => (
                `<option value=${option.value}>${option.label}</option>`
            ))}</select>`)
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "add option" button is clicked -> Opens the appropriate
     * dialog to edit this new option.
     *
     * @private
     */
    _onAddOptionButtonClick: function () {
        const dialog = new SelectOptionDialog(this);
        dialog.on('save', this, option => {
            option.id = optionId;
            optionId++;
            this.selectOptions.push(option);
            this.$('.oe_selectoption_editor').append(
                qweb.render('wysiwyg.widgets.selectoptions.option', { option })
            );
            this._updatePreview();
        });
        dialog.open();
    },
    /**
     * Called when the "delete option" button is clicked -> Deletes this option.
     *
     * @private
     */
    _onDeleteOptionButtonClick: function (ev) {
        const $option = $(ev.currentTarget).closest('[data-option-id]');
        const optionID = parseInt($option.data('option-id'));
        if (optionID) {
            this.selectOptions.splice(this.selectOptions.findIndex(option => option.id === optionID), 1);
        }
        $option.remove();
        this._updatePreview();
    },
    /**
     * Called when the "edit option" button is clicked -> Opens the appropriate
     * dialog to edit this option.
     *
     * @private
     */
    _onEditOptionButtonClick: function (ev) {
        const $option = $(ev.currentTarget).closest('[data-option-id]');
        const optionID = parseInt($option.data('option-id'));
        const option = this.selectOptions.find(option => option.id === optionID);
        if (option) {
            const dialog = new SelectOptionDialog(this, {}, option);
            dialog.on('save', this, updatedOption => {
                option.label = updatedOption.label;
                option.value = updatedOption.value;
                $option.find('.js_option_label').first().text(option.label);
                this._updatePreview();
            });
            dialog.open();
        } else {
            Dialog.alert(null, "Could not find option");
        }
    },
});

var SelectOptionDialog = Dialog.extend({
    template: 'wysiwyg.widgets.selectoption',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/wysiwyg.xml']
    ),

    /**
     * @constructor
     */
    init: function (parent, options, option) {
        this._super(parent, _.extend({
            title: _t("Add an option"),
        }, options || {}));
        this.option = option;
    },
    /**
     * @override
     */
    save: function () {
        this.final_data = {
            label: this.$modal.find('input#o_selectoption_dialog_label_input').val(),
            value: this.$modal.find('input#o_selectoption_dialog_value_input').val(),
        }
        return this._super(...arguments);
    },
});

return SelectOptionsDialog;
});
