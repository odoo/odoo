odoo.define('web.open_studio_button', function (require) {
    "use strict";
    
    var Widget = require('web.Widget');
    var core = require('web.core');
    var Dialog = require('web.Dialog');

    var _t = core._t;
    
    var OpenStudioButton = Widget.extend({
        template: 'web.open_studio_button',
        state_open: false,
        studio_name: 'web_studio',
        events: {
            'click': '_onButtonClick',
        },
        init: function(parent){
            this._super(parent);
        },
        /**
         * @override
         * @private
         */
        _onButtonClick: function (event) {
            event.stopPropagation();
            if(odoo._modules.indexOf(this.studio_name) === -1){
                if(!this.state_open){
                    this.child_widget = new PromoteStudio(this);
                    this.child_widget.insertAfter(this.$el);
                } else {
                    this.child_widget.destroy();
                }
                this.state_open = !this.state_open;
            } else {
                this.trigger_up('studio_icon_clicked');
            }
        }
    });

    var PromoteStudio = Widget.extend({
        events: {
            'click button.o-install-studio': '_onInstallStudio',
        },
        template: 'web.install_web_studio',
        init: function(parent){
            this._super(parent);
        },
        _onInstallStudio: function (ev) {
            ev.stopPropagation();
            var self = this;
            this._rpc({
                model: 'ir.module.module',
                method: 'search_read',
                fields: ['id', 'shortdesc'],
                domain: [['name', '=', self.getParent().studio_name]],
            }).then(function (modules){
                var studio_module_id = modules[0].id;
                var studio_name = modules[0].shortdesc;
                new Dialog(self, {
                    title: _.str.sprintf(_t("Install %(studio_name)s"), {studio_name: studio_name}),
                    size: 'medium',
                    $content: $('<div/>', {
                        text: _.str.sprintf(_t("Do you confirm the installation of %(studio_name)s ?"),
                                                {studio_name: studio_name})})
                         .append($('<a/>', {
                            target: '_blank',
                            href: '/web#id=' + studio_module_id + '&view_type=form&model=ir.module.module&action=base.open_module_tree',
                            text: _t("More info about this app."),
                            class: 'ml4',
                        })
                    ),
                    buttons: [{
                        text: _t("Confirm"),
                        classes: 'btn-primary',
                        click: function () {
                            this.$footer.find('.btn').toggleClass('o_hidden');
                            this._rpc({
                                model: 'ir.module.module',
                                method: 'button_immediate_install',
                                args: [[studio_module_id]],
                            }).then(() => {
                                window.location.reload();
                            }).guardedCatch(reason => {
                                reason.event.preventDefault();
                                this.close();
                                this.displayNotification({
                                    message: _.str.sprintf(_t("Could not install module <strong>%s</strong>"), studio_name),
                                    type: 'danger',
                                    sticky: true,
                                });
                            });
                        },
                    }, {
                        text: _t("Install in progress"),
                        icon: 'fa-spin fa-spinner fa-pulse mr8',
                        classes: 'btn-primary disabled o_hidden',
                    }, {
                        text: _t("Cancel"),
                        close: true,
                    }],
                }).open();
            });
        },
    });
    
    return OpenStudioButton;

});
