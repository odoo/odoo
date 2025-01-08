import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";

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
        const readMore = $('<button class="btn btn-light btn-sm ms-1"/>').text('. . .');
        quoted.first().before(readMore);
        readMore.on('click', () => {
            quoted.toggleClass('visible');
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
        const $container = $link.closest('.o_mg_link_parent');
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
        const $container = $link.closest('.o_mg_link_parent');
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
        rpc($link.data('href'), {
            last_displayed_id: $link.data('last-displayed-id'),
        }).then(function (data) {
            if (!data) {
                return;
            }
            const $threadContainer = $link.parents('.o_mg_replies').first().find('ul.list-unstyled').first();
            if ($threadContainer) {
                const $data = $(data);
                const $lastMsg = $threadContainer.children('li.media').last();
                const $newMessages = $data.find('ul.list-unstyled').first().children('li.media');
                $newMessages.insertAfter($lastMsg);
                $data.find('.o_mg_read_more').parent().appendTo($threadContainer);
            }
            const $showMore = $link.parent();
            $showMore.remove();
        });
     },
});
