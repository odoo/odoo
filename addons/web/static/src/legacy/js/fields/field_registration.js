/** @odoo-module **/

import AbstractField from "web.AbstractField";
import basic_fields from "web.basic_fields";
import relational_fields from "web.relational_fields";
import registry from "web.field_registry";

// Basic fields
registry
    .add('abstract', AbstractField)
    .add('input', basic_fields.InputField)
    .add('integer', basic_fields.FieldInteger)
    .add('boolean', basic_fields.FieldBoolean)
    .add('date', basic_fields.FieldDate)
    .add('datetime', basic_fields.FieldDateTime)
    .add('float', basic_fields.FieldFloat)
    .add('char', basic_fields.FieldChar)
    .add('text', basic_fields.FieldText)
    .add('url', basic_fields.UrlWidget)
    .add('binary', basic_fields.FieldBinaryFile)
    .add('monetary', basic_fields.FieldMonetary)
    .add('percentage', basic_fields.FieldPercentage)
    .add('float_time', basic_fields.FieldFloatTime)
    .add('float_factor', basic_fields.FieldFloatFactor)
    .add('float_toggle', basic_fields.FieldFloatToggle)
    .add('many2one_reference', basic_fields.FieldInteger)

// Relational fields
registry
    .add('many2one', relational_fields.FieldMany2One)
    .add('many2one_avatar', relational_fields.Many2OneAvatar)
    .add('many2many_tags', relational_fields.FieldMany2ManyTags)
    .add('many2many_tags_avatar', relational_fields.FieldMany2ManyTagsAvatar)
    .add('kanban.many2many_tags_avatar', relational_fields.KanbanMany2ManyTagsAvatar)
    .add('list.many2many_tags_avatar', relational_fields.ListMany2ManyTagsAvatar)
    .add('form.many2many_tags', relational_fields.FormFieldMany2ManyTags)
    .add('radio', relational_fields.FieldRadio)
    .add('selection', relational_fields.FieldSelection);
