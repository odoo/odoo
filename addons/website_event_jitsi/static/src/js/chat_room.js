/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(publicWidget.registry.ChatRoom.prototype, {


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onChatRoomClick() {
        if (this.chatRoomProvider === 'jitsi') {
            this._openJitsiChatRoom();
        }
        super._onChatRoomClick();
    },

    _openJitsiChatRoom: async function () {
        this.jitsiServer = this.chatRoomUrl;
        if (this.checkFull) {
            // maybe we didn't refresh the page for a while and so we might join a room
            // which is full, so we perform a RPC call to verify that we can really join
            const isChatRoomFull = await rpc('/chat_room/is_full', { chat_room_name: this.chatRoomName });

            if (isChatRoomFull) {
                window.location.reload();
                return;
            }
        }

        if (await this._openMobileApplication(this.chatRoomName)) {
            // we opened the mobile application
            return;
        }

        await this._loadJisti();

        if (this.attachTo) {
            // attach the Jitsi iframe on the given parent node
            const parentNode = document.querySelector(this.attachTo);
            await this._joinJitsiRoom(parentNode);
        } else {
            // create a modal and append the Jitsi iframe in it
            const jitsiModal = renderToElement('chat_room_modal', {});
            const body = document.querySelector("body")
            body.append(jitsiModal);
            body.classList.add("modal-open");

            const jitsiRoom = await this._joinJitsiRoom(jitsiModal.querySelector('.modal-body'));

            // close the modal when hanging up
            jitsiRoom.addEventListener('videoConferenceLeft', async () => {
                body.querySelector('.o_wjitsi_room_modal').remove();
                body.classList.remove("modal-open");
            });

            // Close the modal when the user dismiss it
            const dismissButton = jitsiModal.querySelector(".modal-footer .btn-primary");
            dismissButton.addEventListener('click', () => {
                jitsiRoom.dispose();
                document.querySelector(".o_wdiscuss_room_modal").remove();
                body.classList.remove("modal-open");
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
      * @param {HTMLElement} jitsiModal, modal element in which we add the Jitsi room
      * @returns {JitsiRoom} the newly created Jitsi room
      */
    _joinJitsiRoom: async function (parentNode) {
        const jitsiRoom = await this._createJitsiRoom(this.chatRoomName, parentNode);
        parentNode.querySelector('.o_wdiscuss_chat_room_loading').remove();
        if (this.defaultUsername) {
            jitsiRoom.executeCommand("displayName", this.defaultUsername);
        }

        let timeoutCall = null;
        const updateParticipantCount = () => {
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
                    this._updateParticipantCount(this.allParticipantIds.length);
                }
            }, timeoutTime);
        };

        jitsiRoom.addEventListener('participantJoined', () => updateParticipantCount());
        jitsiRoom.addEventListener('participantLeft', () => updateParticipantCount());

        // update the participant count when joining the room
        jitsiRoom.addEventListener('videoConferenceJoined', async (event) => {
            this.participantId = event.id;
            updateParticipantCount();

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
                this._updateParticipantCount(this.allParticipantIds.length);
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
    _updateParticipantCount: async function (count) {
        await rpc('/chat_room/update_status', {
            room_name: this.chatRoomName,
            participant_count: count
        });
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
      * Redirect on the Jitsi mobile application if we are on mobile.
      *
      * @private
      * @param {string} chatRoomName
      * @returns {boolean} true is we were redirected to the mobile application
      */
    _openMobileApplication: async function (chatRoomName) {
        if (uiUtils.isSmall()) {
            // we are on mobile, open the room in the application
            window.location = `intent://${this.jitsiServer}/${encodeURIComponent(chatRoomName)}#Intent;scheme=org.jitsi.meet;package=org.jitsi.meet;end`;
            return true;
        }
        return false;
    },

    /**
      * Create a Jitsi room on the given DOM element.
      *
      * @private
      * @param {string} chatRoomName
      * @param {HTMLElement} parentNode
      * @returns {JitsiRoom} the newly created Jitsi room
      */
    _createJitsiRoom: async function (chatRoomName, parentNode) {
      await this._loadJisti();
        const options = {
            roomName: chatRoomName,
            width: "100%",
            height: "100%",
            parentNode: parentNode,
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
