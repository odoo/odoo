odoo.define('website_mail_channel', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.websiteMailChannel = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .o_mg_link_hide': '_onHideLinkClick',
        'click .o_mg_link_show': '_onShowLinkClick',
        'click button.o_mg_read_more': '_onReadMoreClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onHideLinkClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $link = $(ev.currentTarget);
        var $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().hide();
        $container.find('.o_mg_link_show').first().show();
        $container.find('.o_mg_link_content').first().show();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShowLinkClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $link = $(ev.currentTarget);
        var $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().show();
        $container.find('.o_mg_link_show').first().hide();
        $container.find('.o_mg_link_content').first().hide();
    },
    /**
     * @private
     * @param {Event} ev
     */
     _onReadMoreClick: function (ev) {
        var $link = $(ev.target);
        this._rpc({
            route: $link.data('href'),
            params: {
                last_displayed_id: $link.data('msg-id'),
            },
        }).then(function (data) {
            if (!data) {
                return;
            }
            var $threadContainer = $link.parents('.o_mg_replies').first().find('ul.list-unstyled');
            if ($threadContainer) {
                var $lastMsg = $threadContainer.find('li.media').last();
                $(data).find('li.media').insertAfter($lastMsg);
                $(data).find('.o_mg_read_more').parent().appendTo($threadContainer);
            }
            var $showMore = $link.parent();
            $showMore.remove();
            return;
        });
     },
});
});
