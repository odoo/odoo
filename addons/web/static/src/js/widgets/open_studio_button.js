odoo.define('web.open_studio_button', function (require) {
    "use strict";
    
    var Widget = require('web.Widget');
    var core = require('web.core');
    var framework = require('web.framework');

    var _lt = core._lt;
    
    var OpenStudioButton = Widget.extend({
        tagName: 'a',
        className: 'btn btn-default dropdown-item d-none d-md-block',
        icon: "fa-plus",
        state_open: false,
        studio_name: 'web_studio',
        child_widget: undefined,
        events: {
            'click': '_onButtonClick',
        },
        init: function(parent){
            this._super(parent);
        },
        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                var $i = $('<i>').addClass("fa fa-fw")
                                .addClass("o_button_icon")
                                .addClass(self.icon);
                var $span = $('<span>').text(_lt('Add Custom Field'));
                self.$el.append($i).append($span);
            });
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
            'click button.open_install_web_studio': '_open_install_web_studio' 
        },
        template: 'web.install_web_studio',
        init: function(parent){
            this._super(parent);
        },
        _open_install_web_studio: function (ev) {
            ev.preventDefault();
            framework.blockUI();
            var self = this;
            this._rpc({
                model: 'ir.module.module',
                method: 'search_read',
                fields: ['id', 'to_buy'],
                domain: [['name', '=', self.getParent().studio_name]],
            }).then(function (modules){
                var studioModuleID = modules[0].id;
                var toBuy = modules[0].to_buy;
                if(toBuy){
                    framework.unblockUI();
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'ir.module.module',
                        views: [[false, 'form']], 
                        res_id: studioModuleID
                    });
                } else {
                    self._rpc({
                        model: 'ir.module.module',
                        method: 'button_immediate_install',
                        args: [[studioModuleID]],
                    }).then(function() {
                        window.location.reload();
                        framework.unblockUI();
                    }).guardedCatch(reason => {
                        framework.unblockUI();
                        reason.event.preventDefault();
                        self.displayNotification({
                            message: _.str.sprintf(_t("Could not install module <strong>%s</strong>"), name),
                            type: 'danger',
                            sticky: true,
                        });
                    });
                }
            });
        },
    });
    
    return OpenStudioButton;

});
