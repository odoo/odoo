odoo.define('project.update_kanban', function (require) {

var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var session = require('web.session');

var KanbanView = require('web_kanban.KanbanView');
var KanbanRecord = require('web_kanban.Record');

var QWeb = core.qweb;


KanbanRecord.include({
    on_card_clicked: function() {
        if (this.model === 'project.project') {
            this.$('.o_project_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
    on_kanban_action_clicked: function(ev) {
        var self = this;
        if (this.model === 'project.task' && $(ev.currentTarget).data('type') === 'set_cover') {
            ev.preventDefault();

            new Model('ir.attachment').query(['id', 'name'])
               .filter([['res_model', '=', 'project.task'], ['res_id', '=', this.id], ['mimetype', 'ilike', 'image']])
               .all().then(function (attachment_ids) {

                    var $cover_modal = $(QWeb.render("project.SetCoverModal", {
                        widget: self,
                        attachment_ids: attachment_ids,
                    }));

                    $cover_modal.appendTo($('body'));
                    $cover_modal.modal('toggle');
                    $cover_modal.on('click', 'img', function(ev){
                        self.update_record({
                            data : {
                                displayed_image_id: $(ev.currentTarget).data('id'),
                            }
                        });
                        $cover_modal.modal('toggle');
                        $cover_modal.remove();
                    });
            });
        } else {
            this._super.apply(this, arguments, ev);
        }
    },
});
});
