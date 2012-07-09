openerp.survey = function (instance) {
    var QWeb = instance.web.qweb,
    _t = instance.web._t;
    instance.web.ViewManagerAction = instance.web.ViewManagerAction.extend({
        init: function(parent, action) {
            this._super.apply(this,arguments);
            console.log('hello');
        },
        on_mode_switch: function (view_type, no_store, options) {
            var self = this;
            return $.when(this._super.apply(this, arguments)).then(function () {
                var controller = self.views[self.active_view].controller,
                    fvg = controller.fields_view,
                    view_id = (fvg && fvg.view_id) || '--';
                self.$element.find('.oe_debug_view').html(QWeb.render('ViewManagerDebug', {
                    view: controller,
                    view_manager: self
                }));
                if (!self.action.name && fvg) {
                    var title = self.$element.find('.oe_view_title_text');
                    if(!_.isEmpty(title))
                        title = $('.ui-dialog-title');
                        title.text(fvg.arch.attrs.string || fvg.name);
                }
            });
        },
    });
};
