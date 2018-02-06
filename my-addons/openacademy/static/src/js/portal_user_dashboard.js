odoo.define('openacademy.portal_user_dashboard', function (require) {
    'use strict';

    var core = require('web.core');
    var Model = require('web.DataModel');
    var formats = require('web.formats');
    var Widget = require('web.Widget');

    var _t = core._t;
    var QWeb = core.qweb;

    var portal_user_dashboard = Widget.extend({
        'events': {
            'click .o_session_details_link': 'open_session',
            'keyup textarea': 'toggle_send_button',
            'click .o_send_feedback': 'send_feedback'
        },
        init: function (parent) {
            this._super(parent);
            this.academy_session = new Model('openacademy.session');
            this.session_feedback = new Model('openacademy.feedback');
        },
        start: function() {
            var self = this;
            return this._super().then(function() {
                self.render_dashboard();
            });
        },
        willStart: function () {
            var self = this;
            return this._super().then(function () {
                return $.when(self.fetch_data());
            });
        },
        fetch_data: function () {
            var self = this;
            return this.academy_session.query(
                [
                    'name',
                    'start_date',
                    'end_date',
                    'attendee_feedback_ids'
                ]
            )
            .filter([
                ['attendee_ids', 'in', [this.session.partner_id]],
                ['state', 'not in', 'done']
            ])
            .all()
            .done(function (sessions) {
                _(sessions).each(function (session) {
                    session.feedback_done = !_(session.attendee_feedback_ids).isEmpty();
                    session.start_date = formats.format_value(
                        session.start_date, {
                            'type': 'date'
                        }
                    );
                    session.end_date = formats.format_value(
                        session.end_date, {
                            'type': 'date'
                        }
                    );
                });
                self.sessions = sessions;
                self.waiting_feedback_sessions = _(sessions).filter(function (session) {
                    return !session.feedback_done;
                });
            });
        },
        render_dashboard: function () {
            this.$el.empty();
            this.$dashboard = $(QWeb.render('openacademy.portal_user_dashboard', this));
            this.$el.append(this.$dashboard);
            this.$textarea = this.$dashboard.find('textarea');
            this.$send_button = this.$dashboard.find('.o_send_feedback');
        },
        open_session: function (ev) {
            this.do_action({
                'type': 'ir.actions.act_window',
                'res_model': 'openacademy.session',
                'res_id': parseInt($(ev.currentTarget).data('id'), 10),
                'views': [[false, 'form']]
            });
        },
        toggle_send_button: function () {
            var value = this.$textarea.val();
            this.$send_button.prop('disabled', !value);
        },
        send_feedback: function (ev) {
            var self = this;

            var attended_session_id = parseInt($(ev.currentTarget).data('id'), 10);
            var feedback = this.$textarea.val();

            this.session_feedback.call('create', [
                {
                    'session_id': attended_session_id,
                    'attendee_id': this.session.partner_id,
                    'session_feedback': feedback
                }
            ]).done(function (result) {
                self.waiting_feedback_sessions = _(self.sessions).reject(function (session) {
                    if (session.id === attended_session_id) {
                        session.attendee_feedback_ids = [result];
                        session.feedback_done = true;
                        return session;
                    }
                });
                self.render_dashboard();
            });
        },
    });

    core.action_registry.add('openacademy.portal_user_dashboard', portal_user_dashboard);

});
