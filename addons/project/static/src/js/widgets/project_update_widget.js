odoo.define('project.project_update_widget', function (require) {
    "use strict";
    
    var time = require('web.time');
    const fieldRegistry = require('web.field_registry');
    const ListRenderer = require('web.ListRenderer');
    const { FieldOne2Many, FieldMany2One } = require('web.relational_fields');
    var FieldHtml = require('web_editor.field.html');
    const { _lt, qweb } = require('web.core');
    
    var UpdatesLineRenderer = ListRenderer.extend({
        dataRowTemplate: 'project.status_update_data_row',
        countRows: 0,

        /**
         * Renders a empty header
         *
         * @override
         * @private
         */
        _renderHeader: function () {
            return $('<thead/>');
        },

            /**
         * Renders a empty footer
         *
         * @override
         * @private
         */
        _renderFooter: function () {
            return $('<tfoot/>');
        },

        _formatData: function (data) {
            var dateFormat = time.getLangDateFormat();
            var date = data.date && data.date.format(dateFormat) || "";
            return _.extend(data, {
                date: date,
                status_id: data.status_id.data.display_name,
            });
        },

        _renderRow: function (record) {
            this.countRows++;
            return $(qweb.render(this.dataRowTemplate, {
                id: record.id,
                data: this._formatData(record.data),
                is_last: this.countRows === this.state.count,
                is_first: this.countRows === 1,
            }));
        },

        _render: function () {
            var self = this;
            this.countRows = 0;
            return this._super().then(function () {
                self.$el.find('table').removeClass('table-striped o_list_table');
                self.$el.find('table').addClass('o_project_status_table table-borderless');
            });
        },
    });

    var ProjectUpdateOne2ManyField = FieldOne2Many.extend({
        /**
         * @override
         * @private
         */
        _getRenderer: function () {
            return UpdatesLineRenderer;
        },
    });

    var ProjectUpdateMany2OneField = FieldMany2One.extend({
        _template: 'project.status_update',
        events: _.extend({}, FieldMany2One.prototype.events, {
            'click': '_onClick',
        }),

        init: function(parent, field, props){
            this._super.apply(this, arguments);
            this.parent_id = props.data.id;
        },

        willStart: function(){
            const promises = [];
            promises.push(this._super.apply(this, arguments));
            promises.push(this._loadWidgetData());
            return Promise.all(promises);
        },

        
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _loadWidgetData: function(){
            var self = this;
            return this._rpc({
                model: 'project.project',
                method: 'get_last_update_or_default',
                args: [this.parent_id],
            }).then(data => {
                self.data = data;
            });
        },

        _onClick(ev) {
            ev.preventDefault();
            var self = this;
            return this._rpc({
                model: 'project.project',
                method: 'action_open_update_status',
                args: [this.parent_id],
            }).then(action => {
                self.do_action(action);
            });
        },
        
        /**
         * @override
         */
        _renderReadonly() {
            this._super.apply(this, arguments);
            if (this.value) {
                this.$el.html(qweb.render(this._template, {
                    data: this.data,
                }));
            }
        },
    });

    var ProjectUpdateDescriptionField = FieldHtml.extend({
        _template: 'project.desc_see_more',
        _template: 'project.desc_see_less',
        less: true,
        events: _.extend({}, FieldHtml.prototype.events, {
            'click .o_desc_see_more': '_onClickSeeMore',
            'click .o_desc_see_less': '_onClickSeeLess',
        }),

        init: function(){
            this._super.apply(this, arguments);
            this.nbrChar = this.nodeOptions.nbr_char || 100;
        },

        _onClickSeeMore(ev) {
            ev.preventDefault();
            this.less = false;
            this._render();
        },

        _onClickSeeLess(ev) {
            ev.preventDefault();
            this.less = true;
            this._render();
        },

        /**
         * @override
         */
        _renderReadonly() {
            if(!this.value || this.value.length <= this.nbrChar){
                this._super.apply(this, arguments);
                return;
            }
            if(this.old_value) {
                this.value = this.old_value;
            }
            if(this.less) {
                this.old_value = this.value;
                this.value = this.value.substring(0, this._computeEndOfSubstring()) + "<p>...</p>";
            }
            this._super.apply(this, arguments);
            // render button
            if(this.less) {
                var span = $('<span>').addClass('o_desc_see_more');
                span.append($('<a>').text(_lt("See more...")));
                this.$el.append(span);
            } else {
                var span = $('<span>').addClass('o_desc_see_less');
                span.append($('<a>').text(_lt("See less")));
                this.$el.append(span);
            }
        },

        /**
         * It only verifies that we are not inside an html tag.
         * 
         * If we are in an html element, the _super rendering will manage
         *the ending tags so we don't have to take care of html well-formed syntax
         */
        _computeEndOfSubstring() {
            if(this.endOfSubstring){
                return this.endOfSubstring;
            }
            var nextOpeningChevron = this.value.indexOf("<", this.nbrChar);
            var nextEndingChevron = this.value.indexOf(">", this.nbrChar);
            if(nextOpeningChevron > nextEndingChevron){
                this.endOfSubstring = nextEndingChevron + 1;
            } else {
                this.endOfSubstring = this.nbrChar + 1;
            }
            return this.endOfSubstring;
        }
    });
    
    fieldRegistry.add('one2many_project_update', ProjectUpdateOne2ManyField);
    fieldRegistry.add('many2one_project_update', ProjectUpdateMany2OneField);
    fieldRegistry.add('project_html_see_more', ProjectUpdateDescriptionField);

    return {
        ProjectUpdateOne2ManyField,
        ProjectUpdateMany2OneField,
        ProjectUpdateDescriptionField
    };
    
});
