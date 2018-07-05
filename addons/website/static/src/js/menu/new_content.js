odoo.define('website.newMenu', function (require) {
'use strict';

var core = require('web.core');
var websiteNavbarData = require('website.navbar');
var wUtils = require('website.utils');

var qweb = core.qweb;
var _t = core._t;

var NewContentMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        new_page: '_createNewPage',
    }),
    events: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.events || {}, {
        'click > a': '_onMenuToggleClick',
        'click > #o_new_content_menu_choices': '_onBackgroundClick',
    }),

    /**
     * @override
     */
    start: function () {
        this.$newContentMenuChoices = this.$('#o_new_content_menu_choices');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new page to create, then creates it and
     * redirects the user to this new page.
     *
     * @private
     */
    _createNewPage: function () {
        wUtils.prompt({
            id: 'editor_new_page',
            window_title: _t("New Page"),
            input: _t("Page Title"),
            init: function () {
                var $group = this.$dialog.find('div.form-group');
                $group.removeClass('mb0');

                var $add = $('<div/>', {'class': 'form-group mb0'})
                            .append($('<span/>', {'class': 'col-sm-offset-3 col-sm-9 text-left'})
                                    .append(qweb.render('web_editor.components.switch', {id: 'switch_addTo_menu', label: _t("Add page in menu")})));
                $add.find('input').prop('checked', true);
                $group.after($add);
            }
        }).then(function (val, field, $dialog) {
            if (val) {
                var url = '/website/add/' + encodeURIComponent(val);
                if ($dialog.find('input[type="checkbox"]').is(':checked')) url +='?add_menu=1';
                document.location = url;
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the menu's toggle button is clicked -> Opens the menu.
     *
     * @private
     * @param {Event} ev
     */
    _onMenuToggleClick: function (ev) {
        ev.preventDefault();
        this.$newContentMenuChoices.toggleClass('o_hidden');
    },
    /**
     * Called when a click outside the menu's options occurs -> Closes the menu
     *
     * @private
     * @param {Event} ev
     */
    _onBackgroundClick: function (ev) {
        this.$newContentMenuChoices.addClass('o_hidden');
    },
});

websiteNavbarData.websiteNavbarRegistry.add(NewContentMenu, '.o_new_content_menu');

return NewContentMenu;
});
