odoo.define('mail.Chatter', function (require) {
"use strict";

var Activity = require('mail.Activity');
var chat_mixin = require('mail.chat_mixin');
var ChatterComposer = require('mail.ChatterComposer');
var Followers = require('mail.Followers');
var ThreadField = require('mail.ThreadField');
var utils = require('mail.utils');

var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');

var QWeb = core.qweb;

// The purpose of this widget is to display the chatter area below the form view
//
// It instanciates the optional mail_thread, mail_activity and mail_followers widgets.
// It Ensures that those widgets are appended at the right place, and allows them to communicate
// with each other.
// It synchronizes the rendering of those widgets (as they may be asynchronous), to limitate
// the flickering when switching between records
var Chatter = Widget.extend(chat_mixin, {
    template: 'mail.Chatter',
    custom_events: {
        reload_mail_fields: '_onReloadMailFields',
    },
    events: {
        'click .o_chatter_button_new_message': '_onOpenComposerMessage',
        'click .o_chatter_button_log_note': '_onOpenComposerNote',
        'click .o_chatter_button_schedule_activity': '_onScheduleActivity',
    },
    supportedFieldTypes: ['one2many'],

    // inherited
    init: function (parent, record, mailFields, options) {
        this._super.apply(this, arguments);
        this._setState(record);

        this.dp = new concurrency.DropPrevious();

        // mention: get the prefetched partners and use them as mention suggestions
        // if there is a follower widget, the followers will be added to the
        // suggestions as well once fetched
        this.mentionPartnerSuggestions = this._getMentionPartnerSuggestions();
        this.mentionSuggestions = this.mentionPartnerSuggestions;

        this.fields = {};
        if (mailFields.mail_activity) {
            this.fields.activity = new Activity(this, mailFields.mail_activity, record, options);
        }
        if (mailFields.mail_followers) {
            this.fields.followers = new Followers(this, mailFields.mail_followers, record, options);
        }
        if (mailFields.mail_thread) {
            this.fields.thread = new ThreadField(this, mailFields.mail_thread, record, options);
            var nodeAttrs = this.record.fieldAttrs[mailFields.mail_thread];
            var nodeOptions = pyeval.py_eval(nodeAttrs.options || '{}', this.record.data);
            this.hasLogButton = nodeOptions.display_log_button;
        }
    },
    start: function () {
        this.$topbar = this.$('.o_chatter_topbar');

        // render and append the buttons
        this.$topbar.append(QWeb.render('mail.Chatter.Buttons', {
            new_message_btn: !!this.fields.thread,
            log_note_btn: this.hasLogButton,
            schedule_activity_btn: !!this.fields.activity,
        }));

        // start and append the widgets
        var fieldDefs = _.invoke(this.fields, 'appendTo', $('<div>'));
        var def = this.dp.add($.when.apply($, fieldDefs));
        this._render(def).then(this._updateMentionSuggestions.bind(this));

        return this._super.apply(this, arguments);
    },

    // public
    update: function (record, fieldNames) {
        var self = this;

        // close the composer if we switch to another record as it is record dependent
        if (this.record.res_id !== record.res_id) {
            this._closeComposer(true);
        }

        // update the state
        this._setState(record);

        // detach the thread and activity widgets (temporarily force the height to prevent flickering)
        // keep the followers in the DOM as it has a synchronous pre-rendering
        this.$el.height(this.$el.height());
        if (this.fields.activity) {
            this.fields.activity.$el.detach();
        }
        if (this.fields.thread) {
            this.fields.thread.$el.detach();
        }

        // reset and re-append the widgets (and reset 'height: auto' rule)
        // if fieldNames is given, only reset those fields, otherwise reset all fields
        var fieldsToReset;
        if (fieldNames) {
            fieldsToReset = _.filter(this.fields, function (field) {
                return _.contains(fieldNames, field.name);
            });
        } else {
            fieldsToReset = this.fields;
        }
        var fieldDefs = _.invoke(fieldsToReset, 'reset', record);
        var def = this.dp.add($.when.apply($, fieldDefs));
        this._render(def).then(function () {
            self.$el.height('auto');
            self._updateMentionSuggestions();
        });
    },

    // private
    _closeComposer: function (force) {
        if (this.composer && (this.composer.is_empty() || force)) {
            this.composer.do_hide();
            this.composer.clear_composer();
            this._muteNewMessageButton(false);
        }
    },
    _muteNewMessageButton: function (mute) {
        this.$('.o_chatter_button_new_message')
            .toggleClass('btn-primary', !mute)
            .toggleClass('btn-default', mute);
    },
    _openComposer: function (options) {
        var self = this;
        var old_composer = this.composer;
        // create the new composer
        this.composer = new ChatterComposer(this, this.record.model, options.suggested_partners || [], {
            commands_enabled: false,
            context: this.context,
            input_min_height: 50,
            input_max_height: Number.MAX_VALUE, // no max_height limit for the chatter
            input_baseline: 14,
            is_log: options && options.is_log,
            record_name: this.record_name,
            default_body: old_composer && old_composer.$input && old_composer.$input.val(),
            default_mention_selections: old_composer && old_composer.mention_get_listener_selections(),
        });
        this.composer.on('input_focused', this, function () {
            this.composer.mention_set_prefetched_partners(this.mentionSuggestions || []);
        });
        this.composer.insertAfter(this.$('.o_chatter_topbar')).then(function () {
            // destroy existing composer
            if (old_composer) {
                old_composer.destroy();
            }
            if (!config.device.touch) {
                self.composer.focus();
            }
            self.composer.on('post_message', self, function (message) {
                self.fields.thread.postMessage(message).then(self._closeComposer.bind(self, true));
            });
            self.composer.on('need_refresh', self, self.trigger_up.bind(self, 'reload'));
            self.composer.on('close_composer', null, self._closeComposer.bind(self, true));
        });
        this._muteNewMessageButton(true);
    },
    _render: function(def) {
        // the rendering of the chatter is aynchronous: relational data of its fields needs to be
        // fetched (in some case, it might be synchronous as they hold an internal cache).
        // this function takes a deferred as argument, which is resolved once all fields have
        // fetched their data
        // this function appends the fields where they should be once the given deferred is resolved
        // and if it takes more than 500ms, displays a spinner to indicate that it is loading
        var self = this;

        var $spinner = $(QWeb.render('Spinner'));
        concurrency.rejectAfter(concurrency.delay(500), def).then(function () {
            $spinner.appendTo(self.$el);
        });

        return def.then(function () {
            if (self.fields.activity) {
                self.fields.activity.$el.appendTo(self.$el);
            }
            if (self.fields.followers) {
                self.fields.followers.$el.appendTo(self.$topbar);
            }
            if (self.fields.thread) {
                self.fields.thread.$el.appendTo(self.$el);
            }
        }).always($spinner.remove.bind($spinner));
    },
    _setState: function (record) {
        if (!this.record || this.record.res_id !== record.res_id) {
            this.context = {
                default_res_id: record.res_id || false,
                default_model: record.model || false,
            };
            // reset the suggested_partners_def to ensure a reload of the
            // suggested partners when opening the composer on another record
            this.suggested_partners_def = undefined;
        }
        this.record = record;
        this.record_name = record.data.display_name;
    },
    _updateMentionSuggestions: function () {
        if (!this.fields.followers) {
            return;
        }
        var self = this;

        this.mentionSuggestions = [];

        // add the followers to the mention suggestions
        var follower_suggestions = [];
        var followers = this.fields.followers.getFollowers();
        _.each(followers, function (follower) {
            if (follower.res_model === 'res.partner') {
                follower_suggestions.push({
                    id: follower.res_id,
                    name: follower.name,
                    email: follower.email,
                });
            }
        });
        if (follower_suggestions.length) {
            this.mentionSuggestions.push(follower_suggestions);
        }

        // add the partners (followers filtered out) to the mention suggestions
        _.each(this.mentionPartnerSuggestions, function (partners) {
            self.mentionSuggestions.push(_.filter(partners, function (partner) {
                return !_.findWhere(follower_suggestions, { id: partner.id });
            }));
        });
    },

    // handlers
    _onOpenComposerMessage: function () {
        var self = this;
        if (!this.suggested_partners_def) {
            this.suggested_partners_def = $.Deferred();
            var method = 'message_get_suggested_recipients';
            var args = [[this.context.default_res_id], this.context];
            this.rpc(this.record.model, method)
                .args(args)
                .exec()
                .then(function (result) {
                    if (!self.suggested_partners_def) {
                        return; // widget has been reset (e.g. we just switched to another record)
                    }
                    var suggested_partners = [];
                    var thread_recipients = result[self.context.default_res_id];
                    _.each(thread_recipients, function (recipient) {
                        var parsed_email = utils.parse_email(recipient[1]);
                        suggested_partners.push({
                            checked: true,
                            partner_id: recipient[0],
                            full_name: recipient[1],
                            name: parsed_email[0],
                            email_address: parsed_email[1],
                            reason: recipient[2],
                        });
                    });
                    self.suggested_partners_def.resolve(suggested_partners);
                });
        }
        this.suggested_partners_def.then(function (suggested_partners) {
            self._openComposer({ is_log: false, suggested_partners: suggested_partners });
        });
    },
    _onOpenComposerNote: function () {
        this._openComposer({is_log: true});
    },
    _onReloadMailFields: function (event) {
        var fieldNames = [];
        if (this.fields.activity && event.data.activity) {
            fieldNames.push(this.fields.activity.name);
        }
        if (this.fields.followers && event.data.followers) {
            fieldNames.push(this.fields.followers.name);
        }
        if (this.fields.thread && event.data.thread) {
            fieldNames.push(this.fields.thread.name);
        }
        this.trigger_up('reload', {fieldNames: fieldNames});
    },
    _onScheduleActivity: function () {
        this.fields.activity.schedule_activity();
    },
});

return Chatter;

});
