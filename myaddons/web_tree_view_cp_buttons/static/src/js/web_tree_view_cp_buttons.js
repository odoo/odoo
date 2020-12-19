odoo.define('web_tree_view_cp_buttons', function (require) {
    "use strict";

    var ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            var ctx = this.initialState.context;
            if ('tree' in ctx && 'buttons' in ctx.tree) {
                var self = this;
                var tree_buttons = ctx.tree.buttons;
                _.each(tree_buttons, function (button, index) {
                    var $btn = $('<button>', {
                        text: button.name,
                        "class": 'btn btn-secondary o_list_button_extra_' + index + ' ' + button.classes,
                        type: 'button',
                        title: button.name
                    });
                    var attrs = _.extend({ modifiers: {}, options: {} }, $btn.getAttributes(), { type: 'object', name: button.action });
                    self.$buttons.append($btn);
                    self.$buttons.on('click', '.o_list_button_extra_' + index, self._onActionButtonClick.bind(self, attrs));
                });
            }
        },
        _onActionButtonClick: function (attrs, event) {
            event.stopPropagation();
            this.trigger_up('button_clicked', {
                attrs: attrs,
                record: this.model.get(this.handle)
            });
        }
    });

});