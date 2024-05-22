odoo.define('website_slides.unsubscribe_modal', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');
var utils = require('web.utils');

var QWeb = core.qweb;
var _t = core._t;

var SlideUnsubscribeDialog = Dialog.extend({
    template: 'slides.course.unsubscribe.modal',
    _texts: {
        titleSubscribe: _t("Subscribe"),
        titleUnsubscribe: _t("Notifications"),
        titleLeaveCourse: _t("Leave the course")
    },

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: options.isFollower === 'True' ? this._texts.titleSubscribe : this._texts.titleUnsubscribe,
            size: 'medium',
        });
        this._super(parent, options);

        this.set('state', '_subscription');
        this.on('change:state', this, this._onChangeType);

        this.channelID = parseInt(options.channelId, 10);
        this.isFollower = options.isFollower === 'True';
        this.enroll = options.enroll;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$('input#subscribed').prop('checked', self.isFollower);
            self._resetModal();
        });
    },

    getSubscriptionState: function () {
        return this.$('input#subscribed').prop('checked');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _getModalButtons: function () {
        var btnList = [];
        var state = this.get('state');
        if (state === '_subscription') {
            btnList.push({text: _t("Save"), classes: "btn-primary", click: this._onClickSubscriptionSubmit.bind(this)});
            btnList.push({text: _t("Discard"), close: true});
            btnList.push({text: _t("or Leave the course"), classes: "btn-danger ml-auto", click: this._onClickLeaveCourse.bind(this)});
        } else if (state === '_leave') {
            btnList.push({text: _t("Leave the course"), classes: "btn-danger", click: this._onClickLeaveCourseSubmit.bind(this)});
            btnList.push({text: _t("Discard"), click: this._onClickLeaveCourseCancel.bind(this)});
        }
        return btnList;
    },

    /**
     * @private
     */
    _resetModal: function () {
        var state = this.get('state');
        if (state === '_subscription') {
            this.set_title(this.isFollower ? this._texts.titleUnsubscribe : this._texts.titleSubscribe);
            this.$('input#subscribed').prop('checked', this.isFollower);
        }
        else if (state === '_leave') {
            this.set_title(this._texts.titleLeaveCourse);
        }
        this.set_buttons(this._getModalButtons());
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------
    _onClickLeaveCourse: function () {
        this.set('state', '_leave');
    },

    _onClickLeaveCourseCancel: function () {
        this.set('state', '_subscription');
    },

    _onClickLeaveCourseSubmit: function () {
        this._rpc({
            route: '/slides/channel/leave',
            params: {channel_id: this.channelID},
        }).then(function () {
            window.location.reload();
        });
    },

    _onClickSubscriptionSubmit: function () {
        if (this.isFollower === this.getSubscriptionState()) {
            this.destroy();
            return;
        }
        this._rpc({
            route: this.getSubscriptionState() ? '/slides/channel/subscribe' : '/slides/channel/unsubscribe',
            params: {channel_id: this.channelID},
        }).then(function () {
            window.location.reload();
        });
    },

    _onChangeType: function () {
        var currentType = this.get('state');
        var tmpl;
        if (currentType === '_subscription') {
            tmpl = 'slides.course.unsubscribe.modal.subscription';
        } else if (currentType === '_leave') {
            tmpl = 'slides.course.unsubscribe.modal.leave';
        }
        this.$('.o_w_slide_unsubscribe_modal_container').empty();
        this.$('.o_w_slide_unsubscribe_modal_container').append(QWeb.render(tmpl, {widget: this}));

        this._resetModal();
    },
});

publicWidget.registry.websiteSlidesUnsubscribe = publicWidget.Widget.extend({
    selector: '.o_wslides_js_channel_unsubscribe',
    xmlDependencies: ['/website_slides/static/src/xml/website_slides_unsubscribe.xml'],
    events: {
        'click': '_onUnsubscribeClick',
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function ($element) {
        var data = $element.data();
        return new SlideUnsubscribeDialog(this, data).open();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onUnsubscribeClick: function (ev) {
        ev.preventDefault();
        this._openDialog($(ev.currentTarget));
    },
});

return {
    SlideUnsubscribeDialog: SlideUnsubscribeDialog,
    websiteSlidesUnsubscribe: publicWidget.registry.websiteSlidesUnsubscribe
};

});
