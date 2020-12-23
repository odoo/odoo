odoo.define('project.project_update', function (require) {
    "use strict";
    
    const fieldRegistry = require('web.field_registry');
    const { FieldMany2One } = require('web.basic_fields');
    const { _lt } = require('web.core');
    
    const ProjectUpdateField = FieldMany2One.extend({
        
    });
    
    fieldRegistry.add('project_update_field', ProjectUpdateField);
    
    return MarkedAsDoneToggleButton;
    
    });