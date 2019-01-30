odoo.define('mail.systray.ActivityMenu', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var QWeb = core.qweb;

/**
 * Menu item appended in the systray part of the navbar, redirects to the next
 * activities of all app
 */
var ActivityMenu = Widget.extend({
    name: 'activity_menu',
    template:'mail.systray.ActivityMenu',
    events: {
        'click .o_mail_activity_action': '_onActivityActionClick',
        'click .o_mail_preview': '_onActivityFilterClick',
        'show.bs.dropdown': '_onActivityMenuShow',
    },
    willStart: function () {
        return $.when(this.call('mail_service', 'isReady'));
    },
    start: function () {
        this._$activitiesPreview = this.$('.o_mail_systray_dropdown_items');
        this.call('mail_service', 'getMailBus').on('activity_updated', this, this._updateCounter);
        this._updateCounter();
        this._updateActivityPreview();
        return this._super();
    },
    //--------------------------------------------------
    // Private
    //--------------------------------------------------
    /**
     * Make RPC and get current user's activity details
     * @private
     */
    _getActivityData: function () {
        var self = this;

        return self._rpc({
            model: 'res.users',
            method: 'systray_get_activities',
            args: [],
            kwargs: {context: session.user_context},
        }).then(function (data) {
            self._activities = data;
            self.activityCounter = _.reduce(data, function (total_count, p_data) { return total_count + p_data.total_count || 0; }, 0);
            self.$('.o_notification_counter').text(self.activityCounter);
            self.$el.toggleClass('o_no_notification', !self.activityCounter);
        });
    },
    /**
     * Get particular model view to redirect on click of activity scheduled on that model.
     * @private
     * @param {string} model
     */
    _getActivityModelViewID: function (model) {
        return this._rpc({
            model: model,
            method: 'get_activity_view_id'
        });
    },
    /**
     * Update(render) activity system tray view on activity updation.
     * @private
     */
    _updateActivityPreview: function () {
        var self = this;
        self._getActivityData().then(function (){
            self._$activitiesPreview.html(QWeb.render('mail.systray.ActivityMenu.Previews', {
                activities : self._activities
            }));
        });
    },
    /**
     * update counter based on activity status(created or Done)
     * @private
     * @param {Object} [data] key, value to decide activity created or deleted
     * @param {String} [data.type] notification type
     * @param {Boolean} [data.activity_deleted] when activity deleted
     * @param {Boolean} [data.activity_created] when activity created
     */
    _updateCounter: function (data) {
        if (data) {
            if (data.activity_created) {
                this.activityCounter ++;
            }
            if (data.activity_deleted && this.activityCounter > 0) {
                this.activityCounter --;
            }
            this.$('.o_notification_counter').text(this.activityCounter);
            this.$el.toggleClass('o_no_notification', !this.activityCounter);
        }
    },

    //------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------

    /**
     * Redirect to specific action given its xml id
     * @private
     * @param {MouseEvent} ev
     */
    _onActivityActionClick: function (ev) {
        ev.stopPropagation();
        var actionXmlid = $(ev.currentTarget).data('action_xmlid');
        this.do_action(actionXmlid);
    },

    /**
     * Redirect to particular model view
     * @private
     * @param {MouseEvent} event
     */
    _onActivityFilterClick: function (event) {
        // fetch the data from the button otherwise fetch the ones from the parent (.o_mail_preview).
        var data = _.extend({}, $(event.currentTarget).data(), $(event.target).data());
        var context = {};
        if (data.filter === 'my') {
            context['search_default_activities_overdue'] = 1;
            context['search_default_activities_today'] = 1;
        } else {
            context['search_default_activities_' + data.filter] = 1;
        }
        this.do_action({
            type: 'ir.actions.act_window',
            name: data.model_name,
            res_model:  data.res_model,
            views: [[false, 'kanban'], [false, 'form']],
            search_view_id: [false],
            domain: [['activity_user_id', '=', session.uid]],
            context:context,
        });
    },
    /**
     * @private
     */
    _onActivityMenuShow: function () {
         this._updateActivityPreview();
    },
});

SystrayMenu.Items.push(ActivityMenu);

return ActivityMenu;

});
