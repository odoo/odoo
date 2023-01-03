odoo.define('website_jitsi.chat_room', function (require) {
'use strict';

const config = require("web.config");
const core = require('web.core');
const publicWidget = require('web.public.widget');
const QWeb = core.qweb;

publicWidget.registry.ChatRoom = publicWidget.Widget.extend({
    selector: '.o_wjitsi_room_widget',
    events: {
        'click .o_wjitsi_room_link': '_onChatRoomClick',
    },

    /**
      * Manage the chat room (Jitsi), update the participant count...
      *
      * The widget takes some options
      * - 'room-name', the name of the Jitsi room
      * - 'chat-room-id', the ID of the `chat.room` record
      * - 'auto-open', the chat room will be automatically opened when the page is loaded
      * - 'check-full', check if the chat room is full before joining
      * - 'attach-to', a JQuery selector of the element on which we will add the Jitsi
      *                iframe. If nothing is specified, it will open a modal instead.
      * - 'default-username': the username to use in the chat room
      * - 'jitsi-server': the domain name of the Jitsi server to use
      */
    start: async function () {
        await this._super.apply(this, arguments);
        this.roomName = this.$el.data('room-name');
        this.chatRoomId = parseInt(this.$el.data('chat-room-id'));
        // automatically open the current room
        this.autoOpen = parseInt(this.$el.data('auto-open') || 0);
        // before joining, perform a RPC call to verify that the chat room is not full
        this.checkFull = parseInt(this.$el.data('check-full') || 0);
        // query selector of the element on which we attach the Jitsi iframe
        // if not defined, the widget will pop in a modal instead
        this.attachTo = this.$el.data('attach-to') || false;
        // default username for jitsi
        this.defaultUsername = this.$el.data('default-username') || false;

        this.jitsiServer = this.$el.data('jitsi-server') || 'meet.jit.si';

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
            let isChatRoomFull = await this._rpc({
                route: '/jitsi/is_full',
                params: {
                    room_name: this.roomName,
                },
            });

            if (isChatRoomFull) {
                window.location.reload();
                return;
            }
        }

        if (await this._openMobileApplication(this.roomName)) {
            // we opened the mobile application
            return;
        }

        await this._loadJisti();

        if (this.attachTo) {
            // attach the Jitsi iframe on the given parent node
            let $parentNode = $(this.attachTo);
            $parentNode.find("iframe").trigger("empty");
            $parentNode.empty();

            await this._joinJitsiRoom($parentNode);
        } else {
            // create a model and append the Jitsi iframe in it
            let $jitsiModal = $(QWeb.render('chat_room_modal', {}));
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
      * Jitsi do not provide an REST API to get the number of participant in a room.
      * The only way to get the number of participant is to be in the room and to use
      * the Javascript API. So, to update the participant count on the server side,
      * the participant have to send the count in RPC...
      *
      * When leaving a room, the event "participantLeft" is called for the current user
      * once per participant in the room (like if all other participants were leaving the
      * room and then the current user himself).
      *
      * "participantLeft" is called only one time for the other participant who are still
      * in the room.
      *
      * We can not ask the user who is leaving the room to update the participant count
      * because user might close their browser tab without hanging up (and so without
      * triggering the event "videoConferenceLeft"). So, we wait for a moment (because the
      * event "participantLeft" is called many time for the participant who is leaving)
      * and the first participant send the new participant count (so we avoid spamming the
      * server with HTTP requests).
      *
      * We use "setTimout" to send maximum one HTTP request per interval, even if multiple
      * participants join/leave at the same time in the defined interval.
      *
      * Update on the 29 June 2020
      *
      * @private
      * @param {jQuery} $jitsiModal, jQuery modal element in which we add the Jitsi room
      * @returns {JitsiRoom} the newly created Jitsi room
      */
    _joinJitsiRoom: async function ($parentNode) {
        let jitsiRoom = await this._createJitsiRoom(this.roomName, $parentNode);

        if (this.defaultUsername) {
            jitsiRoom.executeCommand("displayName", this.defaultUsername);
        }

        let timeoutCall = null;
        const updateParticipantCount = (joined) => {
            this.allParticipantIds = Object.keys(jitsiRoom._participants).sort();
            // if we reached the maximum capacity, update immediately the participant count
            const timeoutTime = this.allParticipantIds.length >= this.maxCapacity ? 0 : 2000;

            // we clear the old timeout to be sure to call it only once each 2 seconds
            // (so if 2 participants join/leave in this interval, we will perform only
            // one HTTP request for both).
            clearTimeout(timeoutCall);
            timeoutCall = setTimeout(() => {
                this.allParticipantIds = Object.keys(jitsiRoom._participants).sort();
                if (this.participantId === this.allParticipantIds[0]) {
                    // only the first participant of the room send the new participant
                    // count so we avoid to send to many HTTP requests
                    this._updateParticipantCount(this.allParticipantIds.length, joined);
                }
            }, timeoutTime);
        };

        jitsiRoom.addEventListener('participantJoined', () => updateParticipantCount(true));
        jitsiRoom.addEventListener('participantLeft', () => updateParticipantCount(false));

        // update the participant count when joining the room
        jitsiRoom.addEventListener('videoConferenceJoined', async (event) => {
            this.participantId = event.id;
            updateParticipantCount(true);
            $('.o_wjitsi_chat_room_loading').addClass('d-none');

            // recheck if the room is not full
            if (this.checkFull && this.allParticipantIds.length > this.maxCapacity) {
                clearTimeout(timeoutCall);
                jitsiRoom.executeCommand('hangup');
                window.location.reload();
            }
        });

        // update the participant count when using the "Leave" button
        jitsiRoom.addEventListener('videoConferenceLeft', async (event) => {
            this.allParticipantIds = Object.keys(jitsiRoom._participants)
            if (!this.allParticipantIds.length) {
                // bypass the checks and timer of updateParticipantCount
                this._updateParticipantCount(this.allParticipantIds.length, false);
            }
        });

        return jitsiRoom;
    },

    /**
      * Perform an HTTP request to update the participant count on the server side.
      *
      * @private
      * @param {integer} count, current number of participant in the room
      * @param {boolean} joined, true if someone joined the room
      */
    _updateParticipantCount: async function (count, joined) {
        await this._rpc({
            route: '/jitsi/update_status',
            params: {
                room_name: this.roomName,
                participant_count: count,
                joined: joined,
            },
        });
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
      * Redirect on the Jitsi mobile application if we are on mobile.
      *
      * @private
      * @param {string} roomName
      * @returns {boolean} true is we were redirected to the mobile application
      */
    _openMobileApplication: async function (roomName) {
        if (config.device.isMobile) {
            // we are on mobile, open the room in the application
            window.location = `intent://${this.jitsiServer}/${roomName}#Intent;scheme=org.jitsi.meet;package=org.jitsi.meet;end`;
            return true;
        }
        return false;
    },

    /**
      * Create a Jitsi room on the given DOM element.
      *
      * @private
      * @param {string} roomName
      * @param {jQuery} $parentNode
      * @returns {JitsiRoom} the newly created Jitsi room
      */
    _createJitsiRoom: async function (roomName, $parentNode) {
      await this._loadJisti();
        const options = {
            roomName: roomName,
            width: "100%",
            height: "100%",
            parentNode: $parentNode[0],
            configOverwrite: {disableDeepLinking: true},
        };
        return new window.JitsiMeetExternalAPI(this.jitsiServer, options);
    },

    /**
      * Load the Jitsi external library if necessary.
      *
      * @private
      */
    _loadJisti: async function () {
      if (!window.JitsiMeetExternalAPI) {
          await $.ajax({
              url: `https://${this.jitsiServer}/external_api.js`,
              dataType: "script",
          });
      }
    },
});

return publicWidget.registry.ChatRoom;

});
