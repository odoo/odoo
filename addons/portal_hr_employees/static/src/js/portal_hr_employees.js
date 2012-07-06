openerp.portal_hr_employees = function(session) {
    /*
     * Extend the many2many_kanban widget and add it a few things such
     * as delegates.
     */

    // phe: short name for "portal hr employees"
    var phe = session.portal_hr_employees = {};

    phe.many2many_kanban_custom = session.web.form.FieldMany2ManyKanban.extend({
        start: function() {
            var self = this;

            this._super.apply(this, arguments);

            // add events
            this.add_events();
        },
        add_events: function() {
            var self = this;

            // event: make an employee public
            this.$element.delegate('a.oe_employee_make_public', 'click', function (e) {
                console.log('make employee#'+$(this).attr('data-id')+' public');
            });

            // event: make an employee private
            this.$element.delegate('a.oe_employee_make_private', 'click', function (e) {
                console.log('make employee#'+$(this).attr('data-id')+' private');
            });

            // event: make an employee portal
            this.$element.delegate('a.oe_employee_make_portal', 'click', function (e) {
                console.log('make employee#'+$(this).attr('data-id')+' portal');
            });
        },
    });

    session.web.form.widgets.add('many2many_kanban_custom', 'openerp.portal_hr_employees.many2many_kanban_custom');
}
