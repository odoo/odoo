odoo.define('account.AccountCreditNoteButton', function (require) {
"use strict";

var core = require('web.core');
var FormController = require('web.FormController');
var FormView = require('web.FormView');
var ListController = require('web.ListController');
var ListView = require('web.ListView');
var view_registry = require('web.view_registry');

var _t = core._t;

var AccountCreditNoteListController = ListController.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add 'New Credit Note' button and change name of create button in invoice.
     *
     * @override
     * @param {jQuery} $node
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        if (!this.is_action_enabled('create')) {
            return;
        }
        var $createButton = this.$buttons.find('.o_list_button_add');
        var $creditNoteButton = $('<button>', {
            class: 'btn btn-default btn-sm o_button_credit_note',
            accesskey: 'c',
            text: _t('New Credit Note')
        });
        this.isSale = this.initialState.getContext().journal_type === 'sale';
        $createButton.text(this.isSale ? _t('New Invoice') : _t('New Bill'));
        $creditNoteButton.insertAfter($createButton);
        $creditNoteButton.on('click', this._onClickCreditNoteButton.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
    * @private
    */
    _onClickCreditNoteButton: function () {
        var action = this.isSale ? 'account.account_invoice_action_out_refund_new' : 'account.account_invoice_action_in_refund_new';
        this.do_action(action);
    },
});

var AccountCreditNoteListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: AccountCreditNoteListController,
    }),
});

var AccountCreditNoteFormController = FormController.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add 'New Credit Note' button and change name of create button in invoice.
     *
     * @override
     * @param {jQuery} $node
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        if (!this.is_action_enabled('create')) {
            return;
        }
        var $createButton = this.$buttons.find('.o_form_button_create');
        var $creditNoteButton = $('<button>', {
            class: 'btn btn-default btn-sm o_button_credit_note',
            accesskey: 'c',
            text: _t('New Credit Note')
        });
        this.isSale = this.initialState.getContext().journal_type === 'sale';
        $createButton.text(this.isSale ? _t('New Invoice') : _t('New Bill'));
        $creditNoteButton.insertAfter($createButton);
        $creditNoteButton.on('click', this._onClickCreditNoteButton.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
    * @private
    */
    _onClickCreditNoteButton: function () {
        var action = this.isSale ? 'account.account_invoice_action_out_refund_new' : 'account.account_invoice_action_in_refund_new';
        this.do_action(action);
    }
});

var AccountCreditNoteFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AccountCreditNoteFormController,
    }),
});

view_registry.add('credit_note_list_view', AccountCreditNoteListView);
view_registry.add('credit_note_form_view', AccountCreditNoteFormView);

return {
    AccountCreditNoteListController: AccountCreditNoteListController,
    AccountCreditNoteListView: AccountCreditNoteListView,
    AccountCreditNoteFormController: AccountCreditNoteFormController,
    AccountCreditNoteFormView: AccountCreditNoteFormView,
};

});
