odoo.define('website_slides.course.enroll', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');
var _t = core._t;

var SlideEnrollDialog = Dialog.extend({
    template: 'slide.course.join.request',

    init: function (parent, options, modalOptions) {
        modalOptions = _.defaults(modalOptions || {}, {
            title: _t('Request Access.'),
            size: 'medium',
            buttons: [{
                text: _t('Yes'),
                classes: 'btn-primary',
                click: this._onSendRequest.bind(this)
            }, {
                text: _t('Cancel'),
                close: true
            }]
        });
        this.$element = options.$element;
        this.channelId = options.channelId;
        this._super(parent, modalOptions);
    },

    _onSendRequest: function () {
        var self = this;
        this._rpc({
            model: 'slide.channel',
            method: 'action_request_access',
            args: [self.channelId]
        }).then(function (result) {
            if (result.error) {
                self.$element.replaceWith('<div class="alert alert-danger" role="alert"><strong>' + result.error + '</strong></div>');
            } else if (result.done) {
                self.$element.replaceWith('<div class="alert alert-success" role="alert"><strong>' + _t('Request sent !') + '</strong></div>');
            } else {
                self.$element.replaceWith('<div class="alert alert-danger" role="alert"><strong>' + _t('Unknown error, try again.') + '</strong></div>');
            }
            self.close();
        });
    }
    
});

publicWidget.registry.websiteSlidesEnroll = publicWidget.Widget.extend({
    selector: '.o_wslides_js_channel_enroll',
    xmlDependencies: ['/website_slides/static/src/xml/slide_course_join.xml'],
    events: {
        'click': '_onSendRequestClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    
    _openDialog: function (channelId) {
        new SlideEnrollDialog(this, {
            channelId: channelId,
            $element: this.$el
        }).open();
    },
    
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    
    _onSendRequestClick: function (ev) {
        ev.preventDefault();
        this._openDialog($(ev.currentTarget).data('channelId'));
    }
});

return {
    slideEnrollDialog: SlideEnrollDialog,
    websiteSlidesEnroll: publicWidget.registry.websiteSlidesEnroll
};

});
