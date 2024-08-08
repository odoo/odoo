/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.ChatRoom = publicWidget.Widget.extend({
    selector: '.o_wdiscuss_room_widget',
    events: {
        'click .o_wdiscuss_room_link': '_onChatRoomClick',
    },

    /**
      * Manage the chat room
      *
      * The widget takes some options
      * - 'chat-room-name', the name of the discuss room
      * - 'chat-room-id', the ID of the `chat.room` record
      * - 'auto-open', the chat room will be automatically opened when the page is loaded
      * - 'check-full', check if the chat room is full before joining
      * - 'attach-to', a JQuery selector of the element on which we will add the discuss
      *                iframe. If nothing is specified, it will open a modal instead.
      * - 'default-username': the username to use in the chat room
      * - 'chat-room-url': the domain name of the Chat room server to use
      */
    start: async function () {
        await this._super(...arguments);
        this.chatRoomName = this.el.dataset.chatRoomName;
        this.chatRoomProvider = this.el.dataset.chatRoomProvider;
        this.chatRoomId = parseInt(this.el.dataset.chatRoomId);
        // automatically open the current room
        this.autoOpen = parseInt(this.el.dataset.autoOpen || 0);
        // before joining, perform a RPC call to verify that the chat room is not full
        this.checkFull = parseInt(this.el.dataset.checkFull || 0);
        // query selector of the element on which we attach the room iframe
        // if not defined, the widget will pop in a modal instead
        this.attachTo = this.el.dataset.attachTo || false;
        // default username for the room
        this.defaultUsername = this.el.dataset.defaultUsername || false;

        this.chatRoomUrl = this.el.dataset.chatRoomUrl;

        this.maxCapacity = parseInt(this.el.dataset.maxCapacity) || Infinity;

        if (this.autoOpen) {
            await this._onChatRoomClick();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChatRoomClick() {
        if (this.chatRoomProvider === 'discuss') {
            this._openDiscussChatRoom();
        }
    },

    /**
      * Click on a chat room to join it.
      *
      * @private
      */
    _openDiscussChatRoom: async function () {
        if (this.checkFull) {
            // maybe we didn't refresh the page for a while and so we might join a room
            // which is full, so we perform a RPC call to verify that we can really join
            const isChatRoomFull = await rpc('/chat_room/is_full', { chat_room_name: this.chatRoomName });

            if (isChatRoomFull) {
                window.location.reload();
                return;
            }
        }
        let parentNode;
        if (this.attachTo) {
            // attach the discuss iframe on the given parent node
            parentNode = document.querySelector(this.attachTo);
        } else {
            // create a modal and append the iframe in it
            const chatRoomModal = renderToElement('chat_room_modal', {});
            const body = document.querySelector("body")
            body.append(chatRoomModal);
            body.classList.add("modal-open");

            // Close the modal when the user dismiss it
            let dismissButton = chatRoomModal.querySelector(".modal-footer .btn-primary");
            dismissButton.addEventListener('click', () => {
                document.querySelector(".o_wdiscuss_room_modal").remove();
                body.classList.remove("modal-open");
            });

            // attach the discuss iframe on the modal body
            parentNode = chatRoomModal.querySelector(".modal-body");
        }

        const iframe = document.createElement("iframe");
        iframe.style = "height: 100%; width: 100%; border: 0px;";
        iframe.classList.add("d-none");
        iframe.src = this.chatRoomUrl;
        iframe.onload = async () => {
            iframe.classList.remove("d-none");
            parentNode.querySelector(".o_wdiscuss_chat_room_loading").remove();
        };
        parentNode.append(iframe);
    },

});

export default publicWidget.registry.ChatRoom;
