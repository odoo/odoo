odoo.define('project.update_kanban', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var KanbanRecord = require('web.KanbanRecord');

var QWeb = core.qweb;
var _t = core._t;

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'project.project') {
            this.$('.o_project_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onKanbanActionClicked: function (ev) {
        var self = this;
        if (this.modelName === 'project.task' && $(ev.currentTarget).data('type') === 'set_cover') {
            ev.preventDefault();

            var domain = [['res_model', '=', 'project.task'], ['res_id', '=', this.id], ['mimetype', 'ilike', 'image']];
            this._rpc('ir.attachment', 'search_read')
                .withDomain(domain)
                .withFields(['id', 'name'])
                .exec()
                .then(open_cover_images_dialog);
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
                    self._updateRecord({displayed_image_id: $imgs.filter('.o_selected').data('id')});
                }}, {text: _t("Remove Cover Image"), close: true, click: function () {
                    self._updateRecord({displayed_image_id: 0});
                }}, {text: _t("Discard"), close: true}],
                $content: $content,
            }).open();

            var $selectBtn = dialog.$footer.find('.btn-primary');
            $content.on('click', 'img', function (ev) {
                $imgs.not(ev.currentTarget).removeClass('o_selected');
                $selectBtn.prop('disabled', !$(ev.currentTarget).toggleClass('o_selected').hasClass('o_selected'));
            });

            $content.on('dblclick', 'img', function (ev) {
                self._updateRecord({displayed_image_id: $(ev.currentTarget).data('id')});
                dialog.close();
            });
        }
    },
});
});
