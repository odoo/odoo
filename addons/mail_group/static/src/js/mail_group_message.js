odoo.define('mail_group.mail_group_message', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const core = require('web.core');
const _t = core._t;

publicWidget.registry.MailGroupMessage = publicWidget.Widget.extend({
    selector: '.o_mg_message',
    events: {
        'click .o_mg_link_hide': '_onHideLinkClick',
        'click .o_mg_link_show': '_onShowLinkClick',
        'click button.o_mg_read_more': '_onReadMoreClick',
    },

    /**
     * @override
     */
    start: function () {
        // By default hide the mention of the previous email for which we reply
        // And add a button "Read more" to show the mention of the parent email
        const body = this.$el.find('.card-body').first();
        const quoted = body.find('*[data-o-mail-quote]');
        const readMore = $('<button class="btn btn-link"/>').text(_t('Read more'));
        quoted.first().before(readMore);
        quoted.addClass('d-none');
        readMore.on('click', () => {
            quoted.toggleClass('d-none');
        });

        return this._super.apply(this, arguments);
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
        const $link = $(ev.currentTarget);
        const $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().addClass('d-none');
        $container.find('.o_mg_link_show').first().removeClass('d-none');
        $container.find('.o_mg_link_content').first().removeClass('d-none');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShowLinkClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const $link = $(ev.currentTarget);
        const $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().removeClass('d-none');
        $container.find('.o_mg_link_show').first().addClass('d-none');
        $container.find('.o_mg_link_content').first().addClass('d-none');
    },
    /**
     * @private
     * @param {Event} ev
     */
     _onReadMoreClick: function (ev) {
        const $link = $(ev.target);
        this._rpc({
            route: $link.data('href'),
            params: {
                last_displayed_id: $link.data('last-displayed-id'),
            },
        }).then(function (data) {
            if (!data) {
                return;
            }
            const $threadContainer = $link.parents('.o_mg_replies').first().find('ul.list-unstyled');
            if ($threadContainer) {
                const $lastMsg = $threadContainer.find('li.media').last();
                $(data).find('li.media').insertAfter($lastMsg);
                $(data).find('.o_mg_read_more').parent().appendTo($threadContainer);
            }
            const $showMore = $link.parent();
            $showMore.remove();
        });
     },
});
});
