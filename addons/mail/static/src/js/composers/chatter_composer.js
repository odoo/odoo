odoo.define('mail.composer.Chatter', function (require) {
"use strict";

var BasicComposer = require('mail.composer.Basic');
var mailUtils = require('mail.utils');

var core = require('web.core');
var viewDialogs = require('web.view_dialogs');

var _t = core._t;

/**
 * Chat Composer for the Chatter
 *
 * Extends the basic Composer Widget to add 'suggested partner' layer (open
 * popup when suggested partner is selected without email, or other
 * informations), and the button to open the full composer wizard.
 */
var ChatterComposer = BasicComposer.extend({
    template: 'mail.chatter.Composer',
    events: _.extend({}, BasicComposer.prototype.events, {
        'click .o_composer_button_full_composer': '_onOpenFullComposer',
    }),
    init: function (parent, model, suggestedPartners, options) {
        this._super(parent, options);
        this._model = model;
        this.suggestedPartners = suggestedPartners;
        this.options = _.defaults(this.options, {
            display_mode: 'textarea',
            recordName: false,
            isLog: false,
        });
        if (this.options.isLog) {
            this.options.sendText = _t("Log");
        }
        this.notInline = true;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Chatter don't clear message on sent but after successful sent
     *
     * @override
     */
    _clearComposerOnSend: function () {},

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Check the additional partners (not necessary registered partners), and
     * open a popup form view for the ones who informations is missing.
     *
     * @private
     * @param {Array} checkedSuggestedPartners list of 'recipient' partners to
     *   complete informations or validate
     * @returns {Deferred} resolved with the list of checked suggested partners
     *   (real partner)
     **/
    _checkSuggestedPartners: function (checkedSuggestedPartners) {
        var self = this;
        var checkDone = $.Deferred();

        var recipients = _.filter(checkedSuggestedPartners, function (recipient) {
            return recipient.checked;
        });
        var recipientsToFind = _.filter(recipients, function (recipient) {
            return (! recipient.partner_id);
        });
        var namesToFind = _.pluck(recipientsToFind, 'full_name');
        var recipientsToCheck = _.filter(recipients, function (recipient) {
            return (recipient.partner_id && ! recipient.email_address);
        });
        var recipientIDs = _.pluck(_.filter(recipients, function (recipient) {
            return recipient.partner_id && recipient.email_address;
        }), 'partner_id');

        var namesToRemove = [];
        var recipientIDsToRemove = [];

        // have unknown names
        //   -> call message_get_partner_info_from_emails to try to find
        //      partner_id
        var def;
        if (namesToFind.length > 0) {
            def = this._rpc({
                    model: this._model,
                    method: 'message_partner_info_from_emails',
                    args: [[this.context.default_res_id], namesToFind],
                });
        }

        // for unknown names + incomplete partners
        //   -> open popup - cancel = remove from recipients
        $.when(def).pipe(function (result) {
            result = result || [];
            var emailDefs = [];
            var recipientPopups = result.concat(recipientsToCheck);

            _.each(recipientPopups, function (partnerInfo) {
                var deferred = $.Deferred();
                emailDefs.push(deferred);

                var partnerName = partnerInfo.full_name;
                var partnerID = partnerInfo.partner_id;
                var parsedEmail = mailUtils.parseEmail(partnerName);

                var dialog = new viewDialogs.FormViewDialog(self, {
                    res_model: 'res.partner',
                    res_id: partnerID,
                    context: {
                        active_model: self._model,
                        active_id: self.context.default_res_id,
                        force_email: true,
                        ref: 'compound_context',
                        default_name: parsedEmail[0],
                        default_email: parsedEmail[1],
                    },
                    title: _t("Please complete customer's informations"),
                    disable_multiple_selection: true,
                }).open();
                dialog.on('closed', self, function () {
                    deferred.resolve();
                });
                dialog.opened().then(function () {
                    dialog.form_view.on('on_button_cancel', self, function () {
                        namesToRemove.push(partnerName);
                        if (partnerID) {
                            recipientIDsToRemove.push(partnerID);
                        }
                    });
                });
            });
            $.when.apply($, emailDefs).then(function () {
                var newNamesToFind = _.difference(namesToFind, namesToRemove);
                var def;
                if (newNamesToFind.length > 0) {
                    def = self._rpc({
                            model: self._model,
                            method: 'message_partner_info_from_emails',
                            args: [[self.context.default_res_id], newNamesToFind, true],
                        });
                }
                $.when(def).pipe(function (result) {
                    result = result || [];
                    var recipientPopups = result.concat(recipientsToCheck);
                    _.each(recipientPopups, function (partnerInfo) {
                        if (
                            partnerInfo.partner_id &&
                            _.indexOf(partnerInfo.partner_id, recipientIDsToRemove) === -1
                        ) {
                            recipientIDs.push(partnerInfo.partner_id);
                        }
                    });
                }).pipe(function () {
                    checkDone.resolve(recipientIDs);
                });
            });
        });
        return checkDone;
    },
    /**
     * Get the list of selected suggested partners
     *
     * @private
     * @returns {Array} list of 'recipient' selected partners (may not be
     *   created in db)
     **/
    _getCheckedSuggestedPartners: function () {
        var self = this;
        var checkedPartners = [];
        this.$('.o_composer_suggested_partners input:checked').each(function () {
            var fullName = $(this).data('fullname');
            checkedPartners = checkedPartners.concat(
                _.filter(self.suggestedPartners, function (item) {
                    return fullName === item.full_name;
                })
            );
        });
        return checkedPartners;
    },
    /**
     * @override
     * @private
     * @returns {$.Deferred}
     */
    _preprocessMessage: function () {
        var self = this;
        var def = $.Deferred();
        this._super().then(function (message) {
            message = _.extend(message, {
                subtype: 'mail.mt_comment',
                message_type: 'comment',
                context: self.context,
            });

            // Subtype
            if (self.options.isLog) {
                message.subtype = 'mail.mt_note';
            }

            // Partner_ids
            if (!self.options.isLog) {
                var checkedSuggestedPartners = self._getCheckedSuggestedPartners();
                self._checkSuggestedPartners(checkedSuggestedPartners).done(function (partnerIDs) {
                    message.partner_ids = (message.partner_ids || []).concat(partnerIDs);
                    // update context
                    message.context = _.defaults({}, message.context, {
                        mail_post_autofollow: true,
                    });
                    def.resolve(message);
                });
            } else {
                def.resolve(message);
            }

        });

        return def;
    },
    /**
     * @override
     * @private
     */
    _shouldSend: function () {
        return false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onOpenFullComposer: function () {
        if (!this._doCheckAttachmentUpload()){
            return false;
        }

        var self = this;
        var recipientDoneDef = $.Deferred();

        // any operation on the full-composer will reload the record, so
        // warn the user that any unsaved changes on the record will be lost.
        this.trigger_up('discard_record_changes', {
            proceed: function () {
                if (self.options.isLog) {
                    recipientDoneDef.resolve([]);
                } else {
                    var checkedSuggestedPartners = self._getCheckedSuggestedPartners();
                    self._checkSuggestedPartners(checkedSuggestedPartners)
                        .then(recipientDoneDef.resolve.bind(recipientDoneDef));
                }
            },
        });

        recipientDoneDef.then(function (partnerIDs) {
            var context = {
                default_parent_id: self.id,
                default_body: mailUtils.getTextToHTML(self.$input.val()),
                default_attachment_ids: _.pluck(self.get('attachment_ids'), 'id'),
                default_partner_ids: partnerIDs,
                default_is_log: self.options.isLog,
                mail_post_autofollow: true,
            };

            if (self.context.default_model && self.context.default_res_id) {
                context.default_model = self.context.default_model;
                context.default_res_id = self.context.default_res_id;
            }

            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            };
            self.do_action(action, {
                on_close: self.trigger.bind(self, 'need_refresh'),
            }).then(self.trigger.bind(self, 'close_composer'));
        });
    }
});

return ChatterComposer;

});
