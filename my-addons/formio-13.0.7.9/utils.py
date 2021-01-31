# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

def get_field_selection_label(model_obj, field, print_label=False):
    field_def = model_obj.fields_get([field], ['selection', 'string'])[field]

    for r in field_def['selection']:
        if r[0] == getattr(model_obj, field):
            if print_label:
                return '%s: %s' % (field_def['string'], r[1])
            else:
                return '%s' % r[1]
