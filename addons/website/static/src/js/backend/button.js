odoo.define('website.backend.button', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;

// TODO: Remove me when Partner view is adapted to OWL
var WidgetWebsiteButtonIcon = AbstractField.extend({
    template: 'WidgetWebsiteButtonIcon',
    events: {
        'click': '_onClick',
    },

    /**
    * @override
    */
    start: function () {
        this.$icon = this.$('.o_button_icon');
        return this._super.apply(this, arguments);
    },

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
     */
    _render: function () {
        this._super.apply(this, arguments);

        var published = this.value;
        var info = published ? _t("Published") : _t("Unpublished");
        this.$el.attr('aria-label', info)
                .prop('title', info);
        this.$icon.toggleClass('text-danger', !published)
                .toggleClass('text-success', published);
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Redirects to the website page of the record.
     *
     * @private
     */
    _onClick: function () {
        this.trigger_up('button_clicked', {
            attrs: {
                type: 'object',
                name: 'open_website_url',
            },
            record: this.record,
        });
    },
});

field_registry
    .add('website_redirect_button', WidgetWebsiteButtonIcon);
});
