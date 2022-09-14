odoo.define('purchase.ToasterButton', function (require) {
    'use strict';

    const widgetRegistry = require('web.widget_registry');
    const Widget = require('web.Widget');


    const ToasterButton = Widget.extend({
        template: 'purchase.ToasterButton',
        events: Object.assign({}, Widget.prototype.events, {
            'click .fa-info-circle': '_onClickButton',
        }),

        init: function (parent, data, node) {
            this._super(...arguments);
            this.button_name = node.attrs.button_name;
            this.title = node.attrs.title;
            this.id = data.res_id;
            this.model = data.model;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onClickButton: function (ev) {
            this._rpc({
                method: this.button_name,
                model: this.model,
                args: [[this.id]],
            }).then(res => {
                if (res) {
                    this.displayNotification({ message: res.toast_message });
                }
            })
        },
    });

    widgetRegistry.add('toaster_button', ToasterButton);

    return ToasterButton;
});
