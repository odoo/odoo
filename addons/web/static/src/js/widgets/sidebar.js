odoo.define('web.Sidebar', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var Sidebar = Widget.extend({
    init: function(parent, options) {
        var self = this;
        this._super(parent);
        this.options = _.defaults(options || {}, {
            'editable': true
        });
        this.sections = options.sections || [
            {name: 'print', label: _t('Print')},
            {name: 'other', label: _t('Action')},
        ];
        this.items = options.items || {
            print: [],
            other: [],
        };
        this.fileupload_id = _.uniqueId('oe_fileupload');
        $(window).on(this.fileupload_id, function() {
            var args = [].slice.call(arguments).slice(1);
            self.do_attachement_update(self.dataset, self.model_id,args);
            framework.unblockUI();
        });
    },
    start: function() {
        var self = this;
        this._super(this);
        this.$el.addClass('btn-group');
        this.redraw();
        this.$el.on('click','.dropdown-menu li a', function(event) {
            var section = $(this).data('section');
            var index = $(this).data('index');
            var item = self.items[section][index];
            if (item.callback) {
                item.callback.apply(self, [item]);
            } else if (item.action) {
                self.on_item_action_clicked(item);
            } else if (item.url) {
                return true;
            }
            event.preventDefault();
        });
    },
    redraw: function() {
        this.$el.html(QWeb.render('Sidebar', {widget: this}));

        // Hides Sidebar sections when item list is empty
        this.$('.o_dropdown').each(function() {
            if (!$(this).find('li').length) {
                $(this).hide();
            }
        });
        this.$("[title]").tooltip({
            delay: { show: 500, hide: 0}
        });
        this.$('.o_sidebar_add_attachment .o_form_binary_form').change(this.on_attachment_changed);
        this.$('.o_sidebar_delete_attachment').click(this.on_attachment_delete);
    },
    /**
     * For each item added to the section:
     *
     * ``label``
     *     will be used as the item's name in the sidebar, can be html
     *
     * ``action``
     *     descriptor for the action which will be executed, ``action`` and
     *     ``callback`` should be exclusive
     *
     * ``callback``
     *     function to call when the item is clicked in the sidebar, called
     *     with the item descriptor as its first argument (so information
     *     can be stored as additional keys on the object passed to
     *     ``add_items``)
     *
     * ``classname`` (optional)
     *     ``@class`` set on the sidebar serialization of the item
     *
     * ``title`` (optional)
     *     will be set as the item's ``@title`` (tooltip)
     *
     * @param {String} section_code
     * @param {Array<{label, action | callback[, classname][, title]}>} items
     */
    add_items: function(section_code, items) {
        if (items) {
            this.items[section_code].unshift.apply(this.items[section_code],items);
            this.redraw();
        }
    },
    add_toolbar: function(toolbar) {
        var self = this;
        _.each(['print','action','relate'], function(type) {
            var items = toolbar[type];
            if (items) {
                var actions = _.map(items, function (item) {
                    return {
                        label: item.name,
                        action: item,
                    };
                });
                self.add_items(type === 'print' ? 'print' : 'other', actions);
            }
        });
    },
    on_item_action_clicked: function(item) {
        var self = this;
        self.getParent().sidebar_eval_context().done(function (sidebar_eval_context) {
            var ids = self.getParent().get_selected_ids();
            var domain;
            if (self.getParent().get_active_domain) {
                domain = self.getParent().get_active_domain();
            }
            else {
                domain = $.Deferred().resolve(undefined);
            }
            if (ids.length === 0) {
                new Dialog(this, {title: _t("Warning"), size: 'medium', $content: $("<div/>").html(_t("You must choose at least one record."))}).open();
                return false;
            }
            var dataset = self.getParent().dataset;
            var active_ids_context = {
                active_id: ids[0],
                active_ids: ids,
                active_model: dataset.model,
            };

            $.when(domain).done(function (domain) {
                if (domain !== undefined) {
                    active_ids_context.active_domain = domain;
                }
                var c = pyeval.eval('context',
                new data.CompoundContext(
                    sidebar_eval_context, active_ids_context));

                self.rpc("/web/action/load", {
                    action_id: item.action.id,
                    context: new data.CompoundContext(
                        dataset.get_context(), active_ids_context).eval()
                }).done(function(result) {
                    result.context = new data.CompoundContext(
                        result.context || {}, active_ids_context)
                            .set_eval_context(c);
                    result.flags = result.flags || {};
                    result.flags.new_window = true;
                    self.do_action(result, {
                        on_close: function() {
                            // reload view
                            self.getParent().reload();
                        },
                    });
                });
            });
        });
    },
    do_attachement_update: function(dataset, model_id, args) {
        this.dataset = dataset;
        this.model_id = model_id;
        if (args && args[0].error) {
            this.do_warn(_t('Uploading Error'), args[0].error);
        }
        if (!model_id) {
            this.on_attachments_loaded([]);
        } else {
            var dom = [ ['res_model', '=', dataset.model], ['res_id', '=', model_id], ['type', 'in', ['binary', 'url']] ];
            var ds = new data.DataSetSearch(this, 'ir.attachment', dataset.get_context(), dom);
            ds.read_slice(['name', 'url', 'type', 'create_uid', 'create_date', 'write_uid', 'write_date'], {}).done(this.on_attachments_loaded);
        }
    },
    on_attachments_loaded: function(attachments) {
        _.each(attachments,function(a) {
            a.label = a.name;
            if(a.type === "binary") {
                a.url = '/web/content/'  + a.id + '?download=true';
            }
        });
        this.items.files = attachments;
        this.redraw();
    },
    on_attachment_changed: function(e) {
        var $e = $(e.target);
        if ($e.val() !== '') {
            this.$('form.o_form_binary_form').submit();
            $e.parent().find('input[type=file]').prop('disabled', true);
            $e.parent().find('button').prop('disabled', true).find('img, span').toggle();
            this.$('.o_sidebar_add_attachment a').text(_t('Uploading...'));
            framework.blockUI();
        }
    },
    on_attachment_delete: function(e) {
        e.preventDefault();
        e.stopPropagation();
        var self = this;
        var $e = $(e.currentTarget);
        var options = {
            confirm_callback: function () {
                new data.DataSet(this, 'ir.attachment')
                    .unlink([parseInt($e.attr('data-id'), 10)])
                    .done(function() {
                        self.do_attachement_update(self.dataset, self.model_id);
                    });
            }
        };
        Dialog.confirm(this, _t("Do you really want to delete this attachment ?"), options);
    }
});

return Sidebar;

});
