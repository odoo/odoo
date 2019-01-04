odoo.define('account.bank_statement', function(require) {
    "use strict";

    var KanbanController = require("web.KanbanController");
    var ListController = require("web.ListController");

    var includeDict = {
        renderButtons: function () {
            this._super.apply(this, arguments);
            if (this.modelName === "account.bank.statement" && 
                this.searchView &&
                this.searchView.action.env.context &&
                this.searchView.action.env.context.journal_type &&
                this.searchView.action.env.context.journal_type == "bank" ||
                false) {
                this.$buttons.find('button.o_button_import').hide();
            }
        }
    };

    KanbanController.include(includeDict);
    ListController.include(includeDict);
});