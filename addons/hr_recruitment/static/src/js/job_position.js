openerp.hr_recruitment = function (openerp) {
  "use strict";

  openerp.web_kanban.KanbanRecord.include({
      on_card_clicked: function() {
          if (this.view.dataset.model === 'hr.job') {
              this.$('.oe_applications a').first().click();
          } else {
              this._super.apply(this, arguments);
          }
      },
  });

};
