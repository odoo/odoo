odoo.define('website_event_track.website_event_exhibitors', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var QWeb = core.qweb;

/**
 * Small widget responsible for the handling of exhibitors Jitsi rooms.
 * Jitsi allows to easily create video conference rooms for people to tals. More info: https://jitsi.org/
 *
 * If configured, attendees can reach a specific Jitsi room when clicking on the exhibitor logo.
 *
 */
publicWidget.registry.websiteEventExhibitors = publicWidget.Widget.extend({
    selector: '.o_wevent_exhibitor_card',
    xmlDependencies: ['/website_event_track/static/src/xml/event_exhibitor_templates.xml'],
    events: {
        'click .o_wevent_exhibitor_jitsi_link': '_onJitsiLinkClick',
    },

    start: function () {
        var self = this;
        this._super.apply(this, arguments).then(function () {
            self.userName = self.$el.data('userName');
            self.userEmail = self.$el.data('userEmail');
            self.exhibitorName = self.$el.data('exhibitorName');
            self.eventName = self.$el.data('eventName');
            return Promise.resolve();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When clicking the exhibitor logo, open the Jitsi room so that the attendee
     * can reach the exhibitor through a video conference.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onJitsiLinkClick: async function (ev) {
        ev.preventDefault();

        var $jitsiModal = $(QWeb.render('exhibitor_jitsi_modal', {}));
        $jitsiModal.appendTo(this.$el);
        $jitsiModal.modal('show');

        var jitsiRoom = await this._joinJitsiRoom($jitsiModal);
        $jitsiModal.on('hidden.bs.modal', function () {
            jitsiRoom.dispose();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Joins the Jitsi room.
     * The necessary script is downloaded on the fly if necessary.
     *
     * As joining the Jitsi room can take several seconds, a custom loading message
     * is displayed until the attendee successfully joins the video conference.
     *
     * @param {$.Element} $jitsiModal the modal containing the Jitsi iFrame
     */
    _joinJitsiRoom: function ($jitsiModal) {
        var self = this;
        var roomReady;
        var promise = new Promise(function (resolve) {roomReady = resolve;});

        if (window.JitsiMeetExternalAPI) {
            roomReady(self._createJitsiRoom($jitsiModal));
        } else {
            $.ajax({
                url: 'https://meet.jit.si/external_api.js',
                dataType: "script",
                success: function () {
                    roomReady(self._createJitsiRoom($jitsiModal));
                }
            });
        }

        return promise;
    },

    /**
     * Creates the instance of the Jitsi room.
     * It's configured with the user name and email if we're not on a public user.
     *
     * The room name is automatically generated based on the event and exhibitor names.
     *
     * @param {$.Element} $jitsiModal the modal containing the Jitsi iFrame
     */
    _createJitsiRoom: function ($jitsiModal) {
        var domain = 'meet.jit.si';
        var options = {
            roomName: `${this.eventName.replace(/[^a-zA-Z0-9-_]/g, '')}${this.exhibitorName.replace(/[^a-zA-Z0-9-_]/g, '')}`,
            width: '100%',
            height: '100%',
            parentNode: $jitsiModal.find('.modal-body')[0],
            configOverwrite: { disableDeepLinking: true },
        };
        if (this.userEmail && this.userName) {
            options['userInfo'] = {
                email: this.userEmail,
                displayName: this.userName
            };
        }

        var jitsiRoom = new JitsiMeetExternalAPI(domain, options);
        jitsiRoom.addEventListener('videoConferenceJoined', function () {
            $jitsiModal.find('.o_wevent_exhibitor_jitsi_loading').addClass('d-none');
        });

        return jitsiRoom;
    }
});

return publicWidget.registry.websiteEventExhibitors;

});
