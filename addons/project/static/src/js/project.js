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
        if (this.modelName === 'project.project' && this.$(".o_project_kanban_boxes a").length) {
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
            this._rpc({
                    model: 'ir.attachment',
                    method: 'search_read',
                    domain: domain,
                    fields: ['id', 'name'],
                })
                .then(open_cover_images_dialog);
        } else {
            this._super.apply(this, arguments, ev);
        }

        function open_cover_images_dialog(attachment_ids) {
            var coverID = self.record.displayed_image_id && self.record.displayed_image_id.raw_value[0];
            var $content = $(QWeb.render("project.SetCoverModal", {
                cover_id: coverID,
                attachment_ids: attachment_ids,
            }));
            var $imgs = $content.find('img');
            var dialog = new Dialog(self, {
                title: _t("Set a Cover Image"),
                buttons: [{text: _t("Select"), classes: 'btn-primary', close: true, disabled: !coverID, click: function () {
                    var $img = $imgs.filter('.o_selected');
                    var data = {
                        id: $img.data('id'),
                        display_name: $img.data('name')
                    };
                    self._updateRecord({displayed_image_id: data});
                }}, {text: _t("Remove Cover Image"), close: true, click: function () {
                    self._updateRecord({displayed_image_id: false});
                }}, {text: _t("Discard"), close: true}],
                $content: $content,
            });
            dialog.opened().then(function () {
                var $selectBtn = dialog.$footer.find('.btn-primary');
                $content.on('click', 'img', function (ev) {
                    $imgs.not(ev.currentTarget).removeClass('o_selected');
                    $selectBtn.prop('disabled', !$(ev.currentTarget).toggleClass('o_selected').hasClass('o_selected'));
                });

                $content.on('dblclick', 'img', function (ev) {
                    var $img  = $(ev.currentTarget);
                    var data = {
                        id: $img.data('id'),
                        display_name: $img.data('name')
                    };
                    self._updateRecord({displayed_image_id: data});
                    dialog.close();
                });
            });
            dialog.open();
        }
    },
});
});
