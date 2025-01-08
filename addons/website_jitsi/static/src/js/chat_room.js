import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { utils as uiUtils } from "@web/core/ui/ui_service";

/**
 * @typedef jitsiRoom
 * @type {Object}
 * @property {object} _events
 * @property {number} _eventsCount
 * @property {string} _url
 * @property {object} _frame
 * @property {string} _height
 * @property {string} _width
 * @property {object} _transport
 * @property {boolean} _isLargeVideoVisible
 * @property {boolean} _isPrejoinVideoVisible
 * @property {number} _numberOfParticipants
 * @property {object} _participants
 */

export class ChatRoom extends Interaction {
    static selector = ".o_wjitsi_room_widget";
    dynamicContent = {
        ".o_wjitsi_room_link": { "t-on-click": this.onChatRoomClick },
    };

    /**
      * Manage the chat room (Jitsi), update the participant count...
      *
      * The interaction takes some options
      * - 'room-name', the name of the Jitsi room
      * - 'chat-room-id', the ID of the `chat.room` record
      * - 'auto-open', the chat room will be automatically opened when the page is loaded
      * - 'check-full', check if the chat room is full before joining
      * - 'attach-to', a JQuery selector of the element on which we will add the Jitsi
      *                iframe. If nothing is specified, it will open a modal instead.
      * - 'default-username': the username to use in the chat room
      * - 'jitsi-server': the domain name of the Jitsi server to use
      */
    setup() {
        this.roomName = this.el.dataset.roomName;
        this.chatRoomId = parseInt(this.el.dataset.chatRoomId);
        // automatically open the current room
        this.autoOpen = parseInt(this.el.dataset.autoOpen || 0);
        // before joining, perform a RPC call to verify that the chat room is not full
        this.checkFull = parseInt(this.el.dataset.checkFull || 0);
        // query selector of the element on which we attach the Jitsi iframe
        // if not defined, the widget will pop in a modal instead
        this.attachTo = this.el.dataset.attachTo || false;
        // default username for jitsi
        this.defaultUsername = this.el.dataset.defaultUsername || false;

        // FIXME: 'meet.jit.si' should not be used in production.
        this.jitsiServer = this.el.dataset.jitsiServer || 'meet.jit.si';

        this.maxCapacity = parseInt(this.el.dataset.maxCapacity) || Infinity;
    }

    async start() {
        if (this.autoOpen) {
            await this.waitFor(this.onChatRoomClick());
        }
    }

    /**
      * Click on a chat room to join it.
      */
    async onChatRoomClick() {
        if (this.checkFull) {
            // maybe we didn't refresh the page for a while and so we might join a room
            // which is full, so we perform a RPC call to verify that we can really join
            let isChatRoomFull = await this.waitFor(rpc("/jitsi/is_full", { room_name: this.roomName }));

            if (isChatRoomFull) {
                browser.location.reload();
                return;
            }
        }

        if (this.openMobileApplication(this.roomName)) {
            // we opened the mobile application
            return;
        }

        await this.waitFor(this.loadJitsi());

        if (this.attachTo) {
            // attach the Jitsi iframe on the given parent node
            const parentNode = document.querySelector(this.attachTo);
            parentNode.replaceChildren();

            await this.waitFor(this.joinJitsiRoom(parentNode));
        } else {
            // create a modal and append the Jitsi iframe in it
            const jitsiModalEl = this.renderAt("chat_room_modal", {}, document.body)[0];
            const bsJitsiModal = window.Modal.getOrCreateInstance(jitsiModalEl)
            bsJitsiModal.show();
            this.registerCleanup(() => bsJitsiModal.dispose());

            const modalBodyEl = jitsiModalEl.querySelector(".modal-body");
            const jitsiRoom = await this.waitFor(this.joinJitsiRoom(modalBodyEl));

            // close the modal when hanging up
            this.addListener(jitsiRoom, "videoConferenceLeft", () => {
                bsJitsiModal.hide();
            });

            // when the modal is closed, delete the Jitsi room object and clear
            // the DOM
            this.addListener(jitsiModalEl, "hidden.bs.modal", () => {
                bsJitsiModal.dispose();
                jitsiModalEl.remove();
            });
        }
    }

    /**
      * Jitsi does not provide a REST API to get the number of participants in a room.
      * The only way to get the number of participants is to be in the room and to use
      * the Javascript API. So, to update the participant count on the server side,
      * the participants have to send the count through RPC...
      *
      * When leaving a room, the event "participantLeft" is called for the current user
      * once per participant in the room (like if all other participants were leaving the
      * room and then the current user himself).
      *
      * "participantLeft" is called only one time for the other participants who are still
      * in the room.
      *
      * We cannot ask the user who is leaving the room to update the participant count
      * because user might close their browser tab without hanging up (and so without
      * triggering the event "videoConferenceLeft"). So, we wait for a moment (because the
      * event "participantLeft" is called many times for the participant who is leaving)
      * and the first participant sends the new participant count (so we avoid spamming the
      * server with HTTP requests).
      *
      * We use "setTimeout" to send maximum one HTTP request per interval, even if multiple
      * participants join/leave at the same time in the defined interval.
      *
      * Update on the 29 June 2020
      *
      * @param {HTMLElement} parentNode, parent element in which we add the Jitsi room
      * @returns {jitsiRoom} the newly created Jitsi room
      */
    async joinJitsiRoom(parentNode) {
        const jitsiRoom = await this.waitFor(this.createJitsiRoom(this.roomName, parentNode));
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
            timeoutCall = this.waitForTimeout(() => {
                this.allParticipantIds = Object.keys(jitsiRoom._participants).sort();
                if (this.participantId === this.allParticipantIds[0]) {
                    // only the first participant of the room sends the new participant
                    // count so we avoid to send too many HTTP requests
                    this.updateParticipantCount(this.allParticipantIds.length, joined);
                }
            }, timeoutTime);
        };

        this.addListener(jitsiRoom, "participantJoined", () => updateParticipantCount(true));
        this.addListener(jitsiRoom, "participantLeft", () => updateParticipantCount(false));

        // update the participant count when joining the room
        this.addListener(jitsiRoom, "videoConferenceJoined", (event) => {
            this.participantId = event.id;
            updateParticipantCount(true);
            document.querySelector(".o_wjitsi_chat_room_loading")?.classList.add("d-none");

            // recheck if the room is not full
            if (this.checkFull && this.allParticipantIds.length > this.maxCapacity) {
                clearTimeout(timeoutCall);
                jitsiRoom.executeCommand("hangup");
                browser.location.reload();
            }
        });

        // update the participant count when using the "Leave" button
        this.addListener(jitsiRoom, "videoConferenceLeft", () => {
            this.allParticipantIds = Object.keys(jitsiRoom._participants)
            if (!this.allParticipantIds.length) {
                // bypass the checks and timer of updateParticipantCount
                this.updateParticipantCount(this.allParticipantIds.length, false);
            }
        });

        return jitsiRoom;
    }

    /**
      * Perform an HTTP request to update the participant count on the server side.
      *
      * @param {number} count, current number of participant in the room
      * @param {boolean} joined, true if someone joined the room
      */
    async updateParticipantCount(count, joined) {
        await this.waitFor(rpc("/jitsi/update_status", {
            room_name: this.roomName,
            participant_count: count,
            joined: joined,
        }));
    }

    /**
      * Redirect on the Jitsi mobile application if we are on mobile.
      *
      * @param {string} roomName
      * @returns {boolean} true is we were redirected to the mobile application
      */
    openMobileApplication(roomName) {
        if (uiUtils.isSmall()) {
            // we are on mobile, open the room in the application
            browser.location = `intent://${this.jitsiServer}/${encodeURIComponent(roomName)}#Intent;scheme=org.jitsi.meet;package=org.jitsi.meet;end`;
            return true;
        }
        return false;
    }

    /**
      * Create a Jitsi room on the given DOM element.
      *
      * @param {string} roomName
      * @param {HTMLElement} parentNode
      * @returns {jitsiRoom} the newly created Jitsi room
      */
    async createJitsiRoom(roomName, parentNode) {
        await this.waitFor(this.loadJitsi());
        const options = {
            roomName: roomName,
            width: "100%",
            height: "100%",
            parentNode: parentNode,
            configOverwrite: { disableDeepLinking: true },
        };
        return new window.JitsiMeetExternalAPI(this.jitsiServer, options);
    }

    /**
      * Load the Jitsi external library if necessary.
      */
    async loadJitsi() {
        if (!window.JitsiMeetExternalAPI) {
            const scriptEl = document.createElement("script");
            scriptEl.setAttribute("src", `https://${this.jitsiServer}/external_api.js`);
            this.insert(scriptEl, document.head);
            let waitForScriptLoad;
            const prom = new Promise(resolve => waitForScriptLoad = () => resolve());
            this.addListener(scriptEl, "load", waitForScriptLoad);
            await this.waitFor(prom);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_jitsi.chat_room", ChatRoom);
