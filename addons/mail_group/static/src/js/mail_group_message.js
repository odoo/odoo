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
        const bodyEl = this.el.querySelector(".card-body");
        const quotedEls = bodyEl.querySelectorAll("*[data-o-mail-quote]");
        const readMoreBtnEl = document.createElement("button");
        readMoreBtnEl.setAttribute("class", "btn btn-light btn-sm ms-1 o_read_more");
        readMoreBtnEl.textContent = ". . .";
        if (quotedEls.length) {
            quotedEls.parentElement.insertBefore(readMoreBtnEl, quotedEls[0]);
            this.readMoreClick = () => {
                [...quotedEls].forEach((elem) => elem.classList.toggle("visible"));
            };
            readMoreBtnEl.addEventListener("click", this.readMoreClick);
        }

        return this._super.apply(this, arguments);
    },

    destroy() {
        const readMoreBtnEl = this.el.querySelector(".o_read_more");
        readMoreBtnEl.removeEventListener("click", this.readMoreClick);
        this._super(...arguments);
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
        const containerEl = link.closest(".o_mg_link_parent");
        containerEl.querySelector(".o_mg_link_hide").classList.add("d-none");
        containerEl.querySelector(".o_mg_link_show").classList.remove("d-none");
        containerEl.querySelector(".o_mg_link_content").classList.remove("d-none");
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShowLinkClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const link = ev.currentTarget;
        const containerEl = link.closest(".o_mg_link_parent");
        containerEl.querySelector(".o_mg_link_hide").classList.remove("d-none");
        containerEl.querySelector(".o_mg_link_show").classList.add("d-none");
        containerEl.querySelector(".o_mg_link_content").classList.add("d-none");
    },
    /**
     * @private
     * @param {Event} ev
     */
     _onReadMoreClick: function (ev) {
        const link = ev.target;
        rpc(link.getAttribute("data-href"), {
            last_displayed_id: link.getAttribute("data-last-displayed-id"),
        }).then(function (data) {
            if (!data) {
                return;
            }
            function findAncestor(el, sel) {
                while ((el = el.parentElement) && !((el.matches || el.matchesSelector).call(el,sel)));
                return el;
            }
            const repliesElem = findAncestor(link, ".o_mg_replies");
            const threadContainer = repliesElem.querySelector("ul.list-unstyled");
            if (threadContainer) {
                const childEls = threadContainer
                    .querySelectorAll("li.media")
                    .map((elem) => elem.firstChild);
                const lastMsg = childEls[childEls.length - 1];
                const newMessages = data
                    .querySelector("ul.list-unstyled")
                    .querySelectorAll("li.media");
                lastMsg.insertAdjacentHTML("afterEnd", newMessages.outerHTML);
                data.querySelector(".o_mg_read_more").parentElement.appendChild(threadContainer);
            }
            const showMore = link.parent();
            showMore.remove();
        });
     },
});
