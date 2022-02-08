/** @odoo-module **/

import { qweb as QWeb } from 'web.core';
import session  from 'web.session';
import SystrayMenu from 'web.SystrayMenu';
import Widget from 'web.Widget';
import Time from 'web.time';

const { Component } = owl;

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
        'hide.bs.dropdown': '_onActivityMenuHide',
    },
    start: function () {
        this._$activitiesPreview = this.$('.o_mail_systray_dropdown_items');
        Component.env.bus.on('activity_updated', this, this._updateCounter);
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
     * Return views to display when coming from systray depending on the model.
     *
     * @private
     * @param {string} model
     * @returns {Array[]} output the list of views to display.
     */
    _getViewsList(model) {
        return [[false, 'kanban'], [false, 'list'], [false, 'form']];
    },
    /**
     * Update(render) activity system tray view on activity updation.
     * @private
     */
    _updateActivityPreview: function () {
        var self = this;
        self._getActivityData().then(function (){
            self._$activitiesPreview.html(QWeb.render('mail.systray.ActivityMenu.Previews', {
                widget: self,
                Time: Time
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
     * Redirect to specific action given its xml id or to the activity
     * view of the current model if no xml id is provided
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onActivityActionClick: function (ev) {
        ev.stopPropagation();
        this.$('.dropdown-toggle').dropdown('toggle');
        var targetAction = $(ev.currentTarget);
        var actionXmlid = targetAction.data('action_xmlid');
        if (actionXmlid) {
            this.do_action(actionXmlid);
        } else {
            var domain = [['activity_ids.user_id', '=', session.uid]]
            if (targetAction.data('domain')) {
                domain = domain.concat(targetAction.data('domain'))
            }

            this.do_action({
                type: 'ir.actions.act_window',
                name: targetAction.data('model_name'),
                views: [[false, 'activity'], [false, 'kanban'], [false, 'list'], [false, 'form']],
                view_mode: 'activity',
                res_model: targetAction.data('res_model'),
                domain: domain,
            }, {
                clear_breadcrumbs: true,
            });
        }
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
        // Necessary because activity_ids of mail.activity.mixin has auto_join
        // So, duplicates are faking the count and "Load more" doesn't show up
        context['force_search_count'] = 1;

        var domain = [['activity_ids.user_id', '=', session.uid]]
        if (data.domain) {
            domain = domain.concat(data.domain)
        }

        this.do_action({
            type: 'ir.actions.act_window',
            name: data.model_name,
            res_model:  data.res_model,
            views: this._getViewsList(data.res_model),
            search_view_id: [false],
            domain: domain,
            context:context,
        }, {
            clear_breadcrumbs: true,
        });
    },
    /**
     * @private
     */
    _onActivityMenuShow: function () {
        document.body.classList.add('modal-open');
         this._updateActivityPreview();
    },
    /**
     * @private
     */
    _onActivityMenuHide: function () {
        document.body.classList.remove('modal-open');
    },
});

SystrayMenu.Items.push(ActivityMenu);

export default ActivityMenu;
