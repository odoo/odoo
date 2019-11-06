odoo.define('mass_mailing.AddFavorite', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');

var _t = core._t;

var AddFavoriteWidget = AbstractField.extend({
    template: "mass_mailing.favorite_filter",
    events: {
        'click .o_domain_save_button': '_onClickSave',
        'click .o_remove_favorite_filter': '_onClickRemove'
    },
    /**
     * @constructor
     */
    init: function () {
        this.isFavorite = this.value;
        this._super.apply(this, arguments);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @override
     * @private
     */
    _render: function () {
        this.isFavorite = this.value;
        this._setStar(this.isFavorite);
    },
    /**
     * @private
     * @param {boolean} full If the star should be full or not
     */
    _setStar: function (full) { 
        if (full) {
            this.$('.o_add_favorite_filter').hide();
            this.$('.o_remove_favorite_filter').show();
        } else {
            this.$('.o_add_favorite_filter').show();
            this.$('.o_remove_favorite_filter').hide();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _onClickSave: function () {
        var name = this.$('.o_domain_save_name').val();
        if (name.length !== 0) {
            this.trigger_up('mass_mailing_save', {
                filterName: name,
            });
        } else {
            this.do_warn(_t("Warning"), "please enter a name");
        }
    /**
     * @private
     */
    },
    _onClickRemove: function () {
        this.trigger_up('mass_mailing_remove', {});
    },
});

fieldRegistry.add('add_favorite', AddFavoriteWidget);
return AddFavoriteWidget;
});
