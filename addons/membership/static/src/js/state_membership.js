openerp.membership = function(instance) {
	var _t = instance.web._t;
	var QWeb = instance.web.qweb;
	instance.web.form.MembershipState = instance.web.form.FieldSelection.extend({
    	render_value: function() {
            this._super();
            var state = {'invoiced' : 'warning' , 'waiting' : 'warning' , 'none' : 'info' , 'canceled' : 'default' , 'old' : 'default' , 'free' : 'success' , 'paid' : 'success'};
            var found = _.find(this.get('values'), function(el) { return el[0] === this.get("value"); }, this);
            this.$().html(QWeb.render("Widget_membership_state", {'value': found, 'state': state}));
        }
	});
	instance.web.form.widgets = instance.web.form.widgets.extend({
	    'state_membership' : 'instance.web.form.MembershipState',
	});
};
