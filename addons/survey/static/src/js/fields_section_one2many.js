odoo.define('survey.question_page_one2many', function (require) {
"use strict";

var Context = require('web.Context');
var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var FieldRegistry = require('web.field_registry');
var ListRenderer = require('web.ListRenderer');
var config = require('web.config');
var core = require('web.core');

var _t = core._t;

var SectionListRenderer = ListRenderer.extend({
    init: function (parent, state, params) {
        this.sectionFieldName = "is_page";
        this._super.apply(this, arguments);
    },
    _checkIfRecordIsSection: function (id) {
        var record = this._findRecordById(id);
        return record && record.data[this.sectionFieldName];
    },
    _findRecordById: function (id) {
        return _.find(this.state.data, function (record) {
            return record.id === id;
        });
    },
    /**
     * Allows to hide specific field in case the record is a section
     * and, in this case, makes the 'title' field take the space of all the other
     * fields
     * @private
     * @override
     * @param {*} record
     * @param {*} node
     * @param {*} index
     * @param {*} options
     */
    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);

        var isSection = record.data[this.sectionFieldName];

        if (isSection) {
            if (node.attrs.widget === "handle" || node.attrs.name === "random_questions_count") {
                return $cell;
            } else if (node.attrs.name === "title") {
                var nbrColumns = this._getNumberOfCols();
                if (this.handleField) {
                    nbrColumns--;
                }
                if (this.addTrashIcon) {
                    nbrColumns--;
                }
                if (record.data.questions_selection === "random") {
                    nbrColumns--;
                }
                $cell.attr('colspan', nbrColumns);
            } else {
                $cell.removeClass('o_invisible_modifier');
                return $cell.addClass('o_hidden');
            }
        }
        return $cell;
    },
    /**
     * Adds specific classes to rows that are sections
     * to apply custom css on them
     * @private
     * @override
     * @param {*} record
     * @param {*} index
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
        if (record.data[this.sectionFieldName]) {
            $row.addClass("o_is_section");
        }
        return $row;
    },
    /**
     * Adding this class after the view is rendered allows
     * us to limit the custom css scope to this particular case
     * and no other
     * @private
     * @override
     */
    _renderView: function () {
        var def = this._super.apply(this, arguments);
        var self = this;
        return def.then(function () {
            self.$('table.o_list_table').addClass('o_section_list_view');
        });
    },
    // Handlers
    /**
     * Overridden to allow different behaviours depending on
     * the row the user clicked on.
     * If the row is a section: edit inline
     * else use a normal modal
     * @private
     * @override
     * @param {*} ev
     */
    _onRowClicked: function (ev) {
        var parent = this.getParent();
        var recordId = $(ev.currentTarget).data('id');
        var is_section = this._checkIfRecordIsSection(recordId);
        if (is_section && parent.mode === "edit") {
            this.editable = "bottom";
        } else {
            this.editable = null;
        }
        this._super.apply(this, arguments);
    },
    /**
     * Overridden to allow different behaviours depending on
     * the cell the user clicked on.
     * If the cell is part of a section: edit inline
     * else use a normal edit modal
     * @private
     * @override
     * @param {*} ev
     */
    _onCellClick: function (ev) {
        var parent = this.getParent();
        var recordId = $(ev.currentTarget.parentElement).data('id');
        var is_section = this._checkIfRecordIsSection(recordId);
        if (is_section && parent.mode === "edit") {
            this.editable = "bottom";
        } else {
            this.editable = null;
            this.unselectRow();
        }
        this._super.apply(this, arguments);
    },
    /**
     * In this case, navigating in the list caused issues.
     * For example, editing a section then pressing enter would trigger
     * the inline edition of the next element in the list. Which is not desired
     * if the next element ends up being a question and not a section
     * @override
     * @param {*} ev
     */
    _onNavigationMove: function (ev) {
        this.unselectRow();
    },
});

var SectionFieldOne2Many = FieldOne2Many.extend({
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.sectionFieldName = "is_page";
        this.rendered = false;
    },
    /**
     * Overridden to use our custom renderer
     * @private
     * @override
     */
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return SectionListRenderer;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overridden to allow different behaviours depending on
     * the object we want to add. Adding a section would be done inline
     * while adding a question would render a modal.
     * @private
     * @override
     * @param {*} ev
     */
    _onAddRecord: function (ev) {
        this.editable = null;
        if (!config.device.isMobile) {
            var context_str = ev.data.context && ev.data.context[0];
            var context = new Context(context_str).eval();
            if (context['default_' + this.sectionFieldName]) {
                this.editable = "bottom";
            }
        }
        this._super.apply(this, arguments);
    },

    /**
     * Override to perform additional model-specific client-side form validation
     * @override
     * @param {Object} params
     * @param {Object} [params.context]
     * @private
     */
    _openFormDialog: function (params) {
        let onSaved = params["on_saved"];
        let self = this;

        Object.assign(params, {
            on_saved: async function (record){
                let formValues = self._getQuestionFormValues();
                let error = await this._rpc({
                    route: '/survey/validate_entry_fields',
                    params: {'validate_entry_fields': formValues}
                });
                if (error){
                    this.displayNotification({
                        title: _t("Validation Error"),
                        message: error["error"],
                        type: 'danger'
                    });
                    return Promise.reject(error["error"]);
                }
                onSaved(record);
            }
        });
        this._super.apply(this, arguments);
    },

    _getQuestionFormValues: function() {
        return {
            'validation_length_min': Number(document.getElementsByName("validation_length_min")[0].value),
            'validation_length_max': Number(document.getElementsByName("validation_length_max")[0].value),
            'validation_min_float_value': Number(document.getElementsByName("validation_min_float_value")[0].value),
            'validation_max_float_value': Number(document.getElementsByName("validation_max_float_value")[0].value),
            'validation_min_date': document.getElementsByName("validation_min_date")[1].value,
            'validation_max_date': document.getElementsByName("validation_max_date")[1].value,
            'validation_min_datetime': document.getElementsByName("validation_min_datetime")[1].value,
            'validation_max_datetime': document.getElementsByName("validation_max_datetime")[1].value,
            'is_scored_question': document.getElementsByName("is_scored_question")[0].firstElementChild.checked,
            'answer_score': document.getElementsByName('answer_score')[0].value,
            'question_type': document.querySelectorAll("[aria-label='Question Type'] > div > input[checked=true]")[0].dataset['value'],
            'answer_date': document.getElementsByName("answer_date")[1].value
        };
    }
});

FieldRegistry.add('question_page_one2many', SectionFieldOne2Many);
});
