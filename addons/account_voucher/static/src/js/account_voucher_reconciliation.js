openerp.account_voucher = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.account_voucher = {};

    instance.web.form.widgets.add('account_voucher_field', 'instance.web.account_voucher.AccountVoucherField');
    instance.web.account_voucher.AccountVoucherField = instance.web.form.AbstractField.extend({
        template: 'FieldAccountVoucher',
        init: function(field_manager, node) {
            this._super.apply(this, arguments);
            var self = this;
            this.set('value', false);          
        },
        start: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.string = this.get('value') ? _t('Edit') : _t('Create');
            this.node.attrs.icon = this.get('value') ? '/web/static/src/img/icons/gtk-yes.png' : '/web/static/src/img/icons/gtk-no.png';
            this.$button = $(QWeb.render('WidgetButton', {'widget': this}));
            this.$el.append(this.$button);
            this.$button.on('click', self.on_click);
        },
        on_click: function(ev) {
            var self = this;
            ev.stopPropagation();
            var popup =  new instance.web.form.FormOpenPopup(this);
            popup.show_element(
                this.field.relation,
                this.get('value'),
                this.build_context(),
                {title: _t("Voucher: ") + this.string}
            );
            popup.on('create_completed write_completed', self, function(r){
                self.set_value(r);
            });
        },
        set_value: function(value_) {
            var self = this;
            if (value_ instanceof Array) {
                value_ = value_[0];
            }
            value_ = value_ || false;
            this.set('value', value_);
            if (this.is_started) {
                this.render_value();
            }
         },

    });

    instance.web.list.columns.add('field.account_voucher_field', 'instance.web.list.AccountVoucherField');
    instance.web.list.AccountVoucherField = instance.web.list.Column.extend({
        _format: function (row_data, options) {
            if (row_data.voucher_id.value) {
                this.icon = '/web/static/src/img/icons/gtk-yes.png';
            } else {
                this.icon = '/web/static/src/img/icons/gtk-no.png';
            }
            return QWeb.render('FieldAccountVoucher.cell', {'widget': this});
        },
    });

};