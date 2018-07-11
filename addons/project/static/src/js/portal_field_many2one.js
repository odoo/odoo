odoo.define('project.portal_field_many2one', function (require) {

var RelationalFields = require('web.relational_fields');
var FieldMany2One = RelationalFields.FieldMany2One;

/**
 * Performs various overrides on FieldMany2One in order for the link to the project on
 * the form view to redirect to the portal kanban view of the project
 */
FieldMany2One.include({
    /**
     * Add a portal link if the field links to project.project.
     * Otherwise, add the default link.
     *
     * @override
     */
    _renderReadonly: function () {
        this._super.apply(this, arguments);
        if (this.field.relation === 'project.project' && !this.nodeOptions.no_open && this.value) {
            this.$el.attr('href', _.str.sprintf('/my/project/%s%s', this.value.res_id, window.top.location.search));
        };
    },

    /**
     * Prevent the onclick event from bubbling up
     * if the field links to project.project
     *
     * @override
     * @param {MouseEvent} event
     */
    _onClick: function (event) {
        if (this.field.relation !== 'project.project') {
            this._super.apply(this, arguments);
        };
    },
});
});
