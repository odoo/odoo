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
      * Manage the chat room, update the participant count...
      *
      * The widget takes some options
      * - 'room-name', the name of the discuss room
      * - 'chat-room-id', the ID of the `chat.room` record
      * - 'auto-open', the chat room will be automatically opened when the page is loaded
      * - 'check-full', check if the chat room is full before joining
      * - 'attach-to', a JQuery selector of the element on which we will add the discuss
      *                iframe. If nothing is specified, it will open a modal instead.
      * - 'default-username': the username to use in the chat room
      * - 'room-server': the domain name of the Chat room server to use
      */
    start: async function () {
        await this._super.apply(this, arguments);
        this.roomName = this.$el.data('room-name');
        this.chatRoomId = parseInt(this.$el.data('chat-room-id'));
        // automatically open the current room
        this.autoOpen = parseInt(this.$el.data('auto-open') || 0);
        // before joining, perform a RPC call to verify that the chat room is not full
        this.checkFull = parseInt(this.$el.data('check-full') || 0);
        // query selector of the element on which we attach the room iframe
        // if not defined, the widget will pop in a modal instead
        this.attachTo = this.$el.data('attach-to') || false;
        // default username for the room
        this.defaultUsername = this.$el.data('default-username') || false;

        this.roomUrl = this.$el.data('room-url');

        this.maxCapacity = parseInt(this.$el.data('max-capacity')) || Infinity;

        if (this.autoOpen) {
            await this._onChatRoomClick();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
      * Click on a chat room to join it.
      *
      * @private
      */
    _onChatRoomClick: async function () {
        if (this.checkFull) {
            // maybe we didn't refresh the page for a while and so we might join a room
            // which is full, so we perform a RPC call to verify that we can really join
            let isChatRoomFull = await rpc('/chat_room/is_full', { room_name: this.roomName });

            if (isChatRoomFull) {
                window.location.reload();
                return;
            }
        }

        if (this.attachTo) {
            // attach the discuss iframe on the given parent node
            let $parentNode = $(this.attachTo);
            $parentNode.find("iframe").trigger("empty");
            $parentNode.empty();

            const iframe = document.createElement("iframe");
            iframe.style = "height: 100%; width: 100%; border: 0px;"
            iframe.src = this.roomUrl;
            $parentNode.append(iframe);
        } else {
            // create a model and append the Jitsi iframe in it
            let $jitsiModal = $(renderToElement('chat_room_modal', {}));
            $("body").append($jitsiModal);
            $jitsiModal.modal('show');

            let jitsiRoom = await this._joinJitsiRoom($jitsiModal.find('.modal-body'));

            // close the modal when hanging up
            jitsiRoom.addEventListener('videoConferenceLeft', async () => {
                $('.o_wjitsi_room_modal').modal('hide');
            });

            // when the modal is closed, delete the Jitsi room object and clear the DOM
            $jitsiModal.on('hidden.bs.modal', async () => {
                jitsiRoom.dispose();
                $(".o_wjitsi_room_modal").remove();
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
      * Perform an HTTP request to update the participant count on the server side.
      *
      * @private
      * @param {integer} count, current number of participant in the room
      * @param {boolean} joined, true if someone joined the room
      */
    _updateParticipantCount: async function (count, joined) {
        await rpc('/chat_room/update_status', {
            room_name: this.roomName,
            participant_count: count,
            joined: joined,
        });
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

});

export default publicWidget.registry.ChatRoom;
