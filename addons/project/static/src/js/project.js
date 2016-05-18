odoo.define('project.update_kanban', function (require) {
'use strict';

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var Model = require('web.Model');
var session = require('web.session');

var KanbanView = require('web_kanban.KanbanView');
var KanbanRecord = require('web_kanban.Record');

var QWeb = core.qweb;
var _t = core._t;

KanbanRecord.include({
    on_card_clicked: function () {
        if (this.model === 'project.project') {
            this.$('.o_project_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
    on_kanban_action_clicked: function (ev) {
        var self = this;
        if (this.model === 'project.task' && $(ev.currentTarget).data('type') === 'set_cover') {
            ev.preventDefault();

            new Model('ir.attachment').query(['id', 'name'])
               .filter([['res_model', '=', 'project.task'], ['res_id', '=', this.id], ['mimetype', 'ilike', 'image']])
               .all().then(open_cover_images_dialog);
        } else {
            this._super.apply(this, arguments, ev);
        }

        function open_cover_images_dialog(attachment_ids) {
            var cover_id = self.record.displayed_image_id.raw_value[0];
            var $content = $(QWeb.render("project.SetCoverModal", {
                cover_id: cover_id,
                attachment_ids: attachment_ids,
            }));
            var $imgs = $content.find('img');

            var dialog = new Dialog(self, {
                title: _t("Set a Cover Image"),
                buttons: [{text: _t("Select"), classes: 'btn-primary', close: true, disabled: !cover_id, click: function () {
                    self.update_record({data: {displayed_image_id: $imgs.filter('.o_selected').data('id')}});
                }}, {text: _t("Remove Cover Image"), close: true, click: function () {
                    self.update_record({data: {displayed_image_id: 0}});
                }}, {text: _t("Discard"), close: true}],
                $content: $content,
            }).open();

            var $selectBtn = dialog.$footer.find('.btn-primary');
            $content.on('click', 'img', function (ev) {
                $imgs.not(ev.currentTarget).removeClass('o_selected');
                $selectBtn.prop('disabled', !$(ev.currentTarget).toggleClass('o_selected').hasClass('o_selected'));
            });

            $content.on('dblclick', 'img', function (ev) {
                self.update_record({data: {displayed_image_id: $(ev.currentTarget).data('id')}});
                dialog.close();
            });
        }
    },
});
});
