odoo.define('survey.fields_form', function (require) {
"use strict";

var FieldRegistry = require('web.field_registry');
var FieldChar = require('web.basic_fields').FieldChar;

var FormDescriptionPage = FieldChar.extend({

    //--------------------------------------------------------------------------
    // Widget API
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _renderEdit: function () {
        var def = this._super.apply(this, arguments);
        this.$el.addClass('col');
        var $inputGroup = $('<div class="input-group">');
        this.$el = $inputGroup.append(this.$el);
        var $button = $(`
            <button type="button" title="Open section" class="btn oe_edit_only o_icon_button">
                <i class="fa fa-fw o_button_icon fa-external-link"/>
            </button>
        `);
        this.$el = this.$el.append($button);
        $button.on('click', this._onClickEdit.bind(this));

        return def;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickEdit: function (ev) {
        ev.stopPropagation();
        var id = this.record.id;
        if (id) {
            this.trigger_up('open_record', {id: id, target: ev.target});
        }
    },
});

FieldRegistry.add('survey_description_page', FormDescriptionPage);

});
