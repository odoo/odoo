odoo.define('web.field_registry', function (require) {
"use strict";

var Registry = require('web.Registry');

return new Registry();
});

odoo.define('web._field_registry', function(require) {
"use strict";

var AbstractField = require('web.AbstractField');
var basic_fields = require('web.basic_fields');
var relational_fields = require('web.relational_fields');
var registry = require('web.field_registry');


// Basic fields
registry
    .add('abstract', AbstractField)
    .add('input', basic_fields.InputField)
    .add('integer', basic_fields.FieldInteger)
    .add('boolean', basic_fields.FieldBoolean)
    .add('date', basic_fields.FieldDate)
    .add('datetime', basic_fields.FieldDateTime)
    .add('domain', basic_fields.FieldDomain)
    .add('text', basic_fields.FieldText)
    .add('float', basic_fields.FieldFloat)
    .add('char', basic_fields.FieldChar)
    .add('handle', basic_fields.HandleWidget)
    .add('email', basic_fields.EmailWidget)
    .add('phone', basic_fields.FieldPhone)
    .add('url', basic_fields.UrlWidget)
    .add('image', basic_fields.FieldBinaryImage)
    .add('binary', basic_fields.FieldBinaryFile)
    .add('monetary', basic_fields.FieldMonetary)
    .add('priority', basic_fields.PriorityWidget)
    .add('attachment_image', basic_fields.AttachmentImage)
    .add('label_selection', basic_fields.LabelSelection)
    .add('state_selection', basic_fields.StateSelectionWidget)
    .add('boolean_button', basic_fields.FieldBooleanButton)
    .add('statinfo', basic_fields.StatInfo)
    .add('percentpie', basic_fields.FieldPercentPie)
    .add('float_time', basic_fields.FieldFloatTime)
    .add('progressbar', basic_fields.FieldProgressBar)
    .add('toggle_button', basic_fields.FieldToggleBoolean)
    .add('dashboard_graph', basic_fields.JournalDashboardGraph)
    .add('ace', basic_fields.AceEditor);

// Relational fields
registry
    .add('selection', relational_fields.FieldSelection)
    .add('radio', relational_fields.FieldRadio)
    .add('many2one', relational_fields.FieldMany2One)
    .add('list.many2one', relational_fields.ListFieldMany2One)
    .add('kanban.many2one', relational_fields.KanbanFieldMany2One)
    .add('many2many', relational_fields.FieldMany2Many)
    .add('many2many_tags', relational_fields.FieldMany2ManyTags)
    .add('form.many2many_tags', relational_fields.FormFieldMany2ManyTags)
    .add('kanban.many2many_tags', relational_fields.KanbanFieldMany2ManyTags)
    .add('many2many_checkboxes', relational_fields.FieldMany2ManyCheckBoxes)
    .add('one2many', relational_fields.FieldOne2Many)
    .add('statusbar', relational_fields.FieldStatus)
    .add('one2many_list', relational_fields.FieldOne2Many);

});
