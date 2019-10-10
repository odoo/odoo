odoo.define('pos_hr.chrome', function (require) {
    "use strict";

    var core = require('web.core');
    var chrome = require('point_of_sale.chrome');
    var _t = core._t;
    var _lt = core._lt;
    var QWeb = core.qweb;


    /* ------- The User Name Widget ------- */

    // Displays the current cashier's name and allows
    // to switch between cashiers.

    chrome.UsernameWidget.include({
        renderElement: function(){
            var self = this;
            this._super();
            this.$el.click(function(){
                self.click_username();
            });
        },
        click_username: function(){
            if(!this.pos.config.module_pos_hr) { return; }
            var self = this;
            this.gui.select_employee({
                'security':     true,
                'current_employee': this.pos.get_cashier(),
                'title':      _t('Change Cashier'),
            }).then(function(employee){
                self.pos.set_cashier(employee);
                self.chrome.widget.username.renderElement();
                self.renderElement();
            });
        },
    });

    var HeaderCloseButtonWidget = chrome.HeaderButtonWidget.extend({
        start: function(){
            if (this.pos.config.module_pos_hr) {
                var self = this;
                this.pos.bind('change:cashier', this._show_hide_close_button , this);
            }
            return this._super();
        },
        _show_hide_close_button: function(){
            if (this.pos.get('cashier').role == 'manager') {
                this.show();
            } else {
                this.hide();
            }
        }
    });

    var HeaderLockButtonWidget = chrome.HeaderButtonWidget.extend({
        init: function(parent, options) {
        this._super(parent, options);
        this.icon = 'fa-unlock';
        this.icon_color = 'green';
        this.icon_mouseover = 'fa-lock';
        this.icon_color_mouseover = 'red';
        },

        start: function(){
            if (this.pos.config.module_pos_hr) {
                this.show();
            } else {
                this.hide();
            }
            return this._super();
        },

        renderElement: function() {
            var self = this;
            this._super();
            this.iconElement = this.$el.find("i");
            this.$el.css('font-size','20px');
            this.iconElement.addClass(this.icon);
            this.$el.css('color',this.icon_color);
            this.$el.mouseover(function(){
                self.iconElement.addClass(self.icon_mouseover).removeClass(self.icon);
                $(this).css('color', self.icon_color_mouseover);
            }).mouseleave(function(){
                self.iconElement.addClass(self.icon).removeClass(self.icon_mouseover);
                $(this).css('color', self.icon_color);
            });
        },
    });
    chrome.Chrome.include({
        lock_button_widget: {
            'name':   'lock_button',
            'widget': HeaderLockButtonWidget,
            'append':  '.pos-rightheader',
            'args': {
                label: _lt('Lock'),
                action: function() {
                    this.chrome.return_to_login_screen();
                }
            }
        },
        build_widgets: function() {
            var self = this;
                this.widgets.some(function(widget, index){
                    if (widget.name === 'close_button'){
                        widget.widget = HeaderCloseButtonWidget;
                        self.widgets.splice(index, 0, self.lock_button_widget);
                            return true;
                    }
                    return false;
                });
            this._super();
        },
        return_to_login_screen: function() {
            this.gui.show_screen('login');
        },

    });

    return {
        HeaderLockButtonWidget: HeaderLockButtonWidget,
        HeaderCloseButtonWidget: HeaderCloseButtonWidget,
    };
});
