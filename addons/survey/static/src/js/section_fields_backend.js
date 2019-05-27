odoo.define('survey.section_backend', function(require){
    "use strict";

    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var fieldRegistry = require('web.field_registry');
    var ListRenderer = require('web.ListRenderer');

    var SectionListRenderer = ListRenderer.extend({
        _renderBodyCell: function(record, node, index, options){
            var $cell = this._super.apply(this, arguments);

            var isSection = record.data.display_type === 'line_section';

            if(isSection){
                this.editable = "bottom";
                if(node.attrs.widget === "handle"){
                    return $cell;
                } else if(node.attrs.name === "title"){
                    var nbrColumns = this._getNumberOfCols();
                    if(this.handleField){
                        nbrColumns--;
                    }
                    if(this.addTrashIcon){
                        nbrColumns--;
                    }
                    $cell.attr('colSpan', nbrColumns-1);
                } else {
                    return $cell.addClass('o_hidden');
                }
            }else{
                this.editable = false;
            }
            return $cell
        },
        _renderRow: function(record, index){
            var $row = this._super.apply(this, arguments);
            if(record.data.display_type){
                $row.addClass('o_is_' + record.data.display_type);
            }
            return $row;
        },
        _renderView: function(){
            var def = this._super();
            this.$el.find('> table').addClass('o_section_list_view');
            return def;
        },
    });

    var SectionFieldOne2Many = FieldOne2Many.extend({
        _getRenderer: function(){
            if(this.view.arch.tag === 'tree'){
                return SectionListRenderer;
            }
            return this._super.apply(this, arguments);
        },
    });

    fieldRegistry.add('section_one2many', SectionFieldOne2Many);
});