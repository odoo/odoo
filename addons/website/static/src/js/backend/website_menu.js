odoo.define('website.WebsiteMenu', function (require) {
"use strict";

var Widget = require('web.Widget');

var WebsiteMenu = Widget.extend({
    template: 'website.WebsiteMenu',
    events: {
        'click .o_filter_website': '_onFilterWebsiteClick',
    },

    /**
     * @override
     * @param {Widget} parent
     */
    init: function (parent) {
        this._super.apply(this, arguments);
        this.websites = [];
    },

    start: function () {
        this.$menu = this.$('.o_dropdown_menu');
        this._loadWebsites();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @public
     */
    update: function () {
        this.renderElement();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Load existing websites data.
     *
     * @private
     * @returns {Promise[]}
     */
    _loadWebsites: function () {
        var self = this;
        return this._rpc({
            model: 'website',
            method: 'search_read',
            args: [
                [],
                ['name'],
            ],
        }).then(function (result) {
            self.websites = result;
            _.each(result, function (res) {
                var option = $('<a role="menuitem" class="dropdown-item o_filter_website"/>');
                option.attr('data-website-id', res.id).text(res.name);
                self.$menu.append(option);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFilterWebsiteClick: function (ev) {
        var $currentTarget = $(ev.currentTarget);
        this.trigger_up('new_filters', {
            filters: [
                {
                    type: 'website',
                    description: $currentTarget.text().trim(),
                    domain: "[('website_id','='," + $currentTarget.data('website-id') + ")]",
                },
            ],
        });
    },

});

return WebsiteMenu;

});
