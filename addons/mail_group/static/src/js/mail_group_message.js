/** @odoo-module **/

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
        const body = this.el.querySelector('.card-body');
        const quoted = body.querySelectorAll('*[data-o-mail-quote]');
        const readMore = document.createElement('button');
        readMore.setAttribute('class', 'btn btn-light btn-sm ms-1');
        readMore.textContent = '. . .';
        document.insertBefore(readMore, quoted[0]);
        readMore.addEventListener('click', () => {
            [...quoted].forEach((elem) => elem.classList.toggle('visible'));
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
        const link = ev.currentTarget;
        const container = link.closest('.o_mg_link_parent');
        container.querySelector('.o_mg_link_hide').classList.add('d-none');
        container.querySelector('.o_mg_link_show').classList.remove('d-none');
        container.querySelector('.o_mg_link_content').classList.remove('d-none');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShowLinkClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const link = ev.currentTarget;
        const container = link.closest('.o_mg_link_parent');
        container.querySelector('.o_mg_link_hide').classList.remove('d-none');
        container.querySelector('.o_mg_link_show').classList.add('d-none');
        container.querySelector('.o_mg_link_content').classList.add('d-none');
    },
    /**
     * @private
     * @param {Event} ev
     */
     _onReadMoreClick: function (ev) {
        const link = ev.target;
        rpc(link.getAttribute('data-href'), {
            last_displayed_id: link.getAttribute('data-last-displayed-id'),
        }).then(function (data) {
            if (!data) {
                return;
            }
            function findAncestor (el, sel) {
                while ((el = el.parentElement) && !((el.matches || el.matchesSelector).call(el,sel)));
                return el;
            }
            const repliesElem = findAncestor(link, '.o_mg_replies');
            const threadContainer = repliesElem.querySelector('ul.list-unstyled');
            if (threadContainer) {
                // TODO: MSH: Need to find children method's alternative
                const lastMsg = $(threadContainer).children('li.media').last()[0];
                const newMessages = $(data.querySelector('ul.list-unstyled')).children('li.media');
                lastMsg.insertAdjacentHTML('afterEnd', newMessages.outerHTML)
                data.querySelector('.o_mg_read_more').parent().appendChild(threadContainer);
            }
            const showMore = link.parent();
            showMore.remove();
        });
     },
});
