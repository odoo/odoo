odoo.define('website.backend.button', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;

var WidgetWebsiteButton = AbstractField.extend({
    template: 'WidgetWebsiteButton',

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        this._super.apply(this, arguments);

        var $value = this.$('.o_value');
        var published = (this.value === true);
        $value.html(published ? _t("Published") : _t("Unpublished"))
              .toggleClass('text-danger', !published)
              .toggleClass('text-success', published);
    },
});

field_registry.add('website_button', WidgetWebsiteButton);
});
