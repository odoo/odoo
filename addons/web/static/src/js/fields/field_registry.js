odoo.define('web.field_registry', function (require) {
"use strict";

var Registry = require('web.Registry');

return new Registry();
});

odoo.define('web._field_registry', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var basic_fields = require('web.basic_fields');
var relational_fields = require('web.relational_fields');
var registry = require('web.field_registry');
var special_fields = require('web.special_fields');


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
    .add('list.text', basic_fields.ListFieldText)
    .add('html', basic_fields.FieldText)
    .add('float', basic_fields.FieldFloat)
    .add('char', basic_fields.FieldChar)
    .add('link_button', basic_fields.LinkButton)
    .add('handle', basic_fields.HandleWidget)
    .add('email', basic_fields.FieldEmail)
    .add('phone', basic_fields.FieldPhone)
    .add('url', basic_fields.UrlWidget)
    .add('CopyClipboardText', basic_fields.TextCopyClipboard)
    .add('CopyClipboardChar', basic_fields.CharCopyClipboard)
    .add('image', basic_fields.FieldBinaryImage)
    .add('binary', basic_fields.FieldBinaryFile)
    .add('pdf_viewer', basic_fields.FieldPdfViewer)
    .add('monetary', basic_fields.FieldMonetary)
    .add('percentage', basic_fields.FieldPercentage)
    .add('priority', basic_fields.PriorityWidget)
    .add('attachment_image', basic_fields.AttachmentImage)
    .add('label_selection', basic_fields.LabelSelection)
    .add('kanban_label_selection', basic_fields.LabelSelection) // deprecated, use label_selection
    .add('state_selection', basic_fields.StateSelectionWidget)
    .add('kanban_state_selection', basic_fields.StateSelectionWidget) // deprecated, use state_selection
    .add('boolean_favorite', basic_fields.FavoriteWidget)
    .add('boolean_button', basic_fields.FieldBooleanButton)
    .add('boolean_toggle', basic_fields.BooleanToggle)
    .add('statinfo', basic_fields.StatInfo)
    .add('percentpie', basic_fields.FieldPercentPie)
    .add('float_time', basic_fields.FieldFloatTime)
    .add('float_factor', basic_fields.FieldFloatFactor)
    .add('float_toggle', basic_fields.FieldFloatToggle)
    .add('progressbar', basic_fields.FieldProgressBar)
    .add('toggle_button', basic_fields.FieldToggleBoolean)
    .add('dashboard_graph', basic_fields.JournalDashboardGraph)
    .add('ace', basic_fields.AceEditor);

// Relational fields
registry
    .add('selection', relational_fields.FieldSelection)
    .add('radio', relational_fields.FieldRadio)
    .add('selection_badge', relational_fields.FieldSelectionBadge)
    .add('many2one', relational_fields.FieldMany2One)
    .add('many2one_barcode', relational_fields.FieldMany2One)
    .add('list.many2one', relational_fields.ListFieldMany2One)
    .add('kanban.many2one', relational_fields.KanbanFieldMany2One)
    .add('many2many', relational_fields.FieldMany2Many)
    .add('many2many_binary', relational_fields.FieldMany2ManyBinaryMultiFiles)
    .add('many2many_tags', relational_fields.FieldMany2ManyTags)
    .add('form.many2many_tags', relational_fields.FormFieldMany2ManyTags)
    .add('kanban.many2many_tags', relational_fields.KanbanFieldMany2ManyTags)
    .add('many2many_checkboxes', relational_fields.FieldMany2ManyCheckBoxes)
    .add('one2many', relational_fields.FieldOne2Many)
    .add('statusbar', relational_fields.FieldStatus)
    .add('reference', relational_fields.FieldReference)
    .add('one2many_list', relational_fields.FieldOne2Many);

// Special fields
registry
    .add('timezone_mismatch', special_fields.FieldTimezoneMismatch)
    .add('report_layout', special_fields.FieldReportLayout);
});
