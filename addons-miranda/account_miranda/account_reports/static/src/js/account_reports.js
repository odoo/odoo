odoo.define('account_reports.account_report', function (require) {
'use strict';

var core = require('web.core');
var Context = require('web.Context');
var AbstractAction = require('web.AbstractAction');
var Dialog = require('web.Dialog');
var datepicker = require('web.datepicker');
var session = require('web.session');
var field_utils = require('web.field_utils');
var RelationalFields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var WarningDialog = require('web.CrashManager').WarningDialog;
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var M2MFilters = Widget.extend(StandaloneFieldManagerMixin, {
    /**
     * @constructor
     * @param {Object} fields
     */
    init: function (parent, fields) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.fields = fields;
        this.widgets = {};
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        _.each(this.fields, function (field, fieldName) {
            defs.push(self._makeM2MWidget(field, fieldName));
        });
        return Promise.all(defs);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var $content = $(QWeb.render("m2mWidgetTable", {fields: this.fields}));
        self.$el.append($content);
        _.each(this.fields, function (field, fieldName) {
            self.widgets[fieldName].appendTo($content.find('#'+fieldName+'_field'));
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method will be called whenever a field value has changed and has
     * been confirmed by the model.
     *
     * @private
     * @override
     * @returns {Promise}
     */
    _confirmChange: function () {
        var self = this;
        var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
        var data = {};
        _.each(this.fields, function (filter, fieldName) {
            data[fieldName] = self.widgets[fieldName].value.res_ids;
        });
        this.trigger_up('value_changed', data);
        return result;
    },
    /**
     * This method will create a record and initialize M2M widget.
     *
     * @private
     * @param {Object} fieldInfo
     * @param {string} fieldName
     * @returns {Promise}
     */
    _makeM2MWidget: function (fieldInfo, fieldName) {
        var self = this;
        var options = {};
        options[fieldName] = {
            options: {
                no_create_edit: true,
                no_create: true,
            }
        };
        return this.model.makeRecord(fieldInfo.modelName, [{
            fields: [{
                name: 'id',
                type: 'integer',
            }, {
                name: 'display_name',
                type: 'char',
            }],
            name: fieldName,
            relation: fieldInfo.modelName,
            type: 'many2many',
            value: fieldInfo.value,
        }], options).then(function (recordID) {
            self.widgets[fieldName] = new RelationalFields.FieldMany2ManyTags(self,
                fieldName,
                self.model.get(recordID),
                {mode: 'edit',}
            );
            self._registerWidget(recordID, fieldName, self.widgets[fieldName]);
        });
    },
});

var accountReportsWidget = AbstractAction.extend({
    hasControlPanel: true,

    events: {
        'input .o_account_reports_filter_input': 'filter_accounts',
        'click .o_account_reports_summary': 'edit_summary',
        'click .js_account_report_save_summary': 'save_summary',
        'click .o_account_reports_footnote_icons': 'delete_footnote',
        'click .js_account_reports_add_footnote': 'add_edit_footnote',
        'click .js_account_report_foldable': 'fold_unfold',
        'click [action]': 'trigger_action',
        'click .o_account_reports_load_more span': 'load_more',
        'click .o_account_reports_table thead th': 'selected_column',
        'click .o_change_expected_date': '_onChangeExpectedDate',
    },

    custom_events: {
        'value_changed': function(ev) {
             var self = this;
             self.report_options.partner_ids = ev.data.partner_ids;
             self.report_options.partner_categories = ev.data.partner_categories;
             self.report_options.analytic_accounts = ev.data.analytic_accounts;
             self.report_options.analytic_tags = ev.data.analytic_tags;
             return self.reload().then(function () {
                 self.$searchview_buttons.find('.account_partner_filter').click();
                 self.$searchview_buttons.find('.account_analytic_filter').click();
             });
         },
    },

    init: function(parent, action) {
        this.actionManager = parent;
        this.report_model = action.context.model;
        if (this.report_model === undefined) {
            this.report_model = 'account.report';
        }
        this.financial_id = false;
        if (action.context.id) {
            this.financial_id = action.context.id;
        }
        this.odoo_context = action.context;
        this.report_options = action.options || false;
        this.ignore_session = action.ignore_session;
        if ((action.ignore_session === 'read' || action.ignore_session === 'both') !== true) {
            var persist_key = 'report:'+this.report_model+':'+this.financial_id+':'+session.company_id;
            this.report_options = JSON.parse(sessionStorage.getItem(persist_key)) || this.report_options;
        }
        return this._super.apply(this, arguments);
    },
    start: function() {
        var self = this;
        var extra_info = this._rpc({
                model: self.report_model,
                method: 'get_report_informations',
                args: [self.financial_id, self.report_options],
                context: self.odoo_context,
            })
            .then(function(result){
                return self.parse_reports_informations(result);
            });
        return Promise.all([extra_info, this._super.apply(this, arguments)]).then(function() {
            self.render();
        });
    },
    parse_reports_informations: function(values) {
        this.report_options = values.options;
        this.odoo_context = values.context;
        this.report_manager_id = values.report_manager_id;
        this.footnotes = values.footnotes;
        this.buttons = values.buttons;

        this.main_html = values.main_html;
        this.$searchview_buttons = $(values.searchview_html);
        this.persist_options();
    },
    persist_options: function() {
        if ((this.ignore_session === 'write' || this.ignore_session === 'both') !== true) {
            var persist_key = 'report:'+this.report_model+':'+this.financial_id+':'+session.company_id;
            sessionStorage.setItem(persist_key, JSON.stringify(this.report_options));
        }
    },
    // We need this method to rerender the control panel when going back in the breadcrumb
    do_show: function() {
        this._super.apply(this, arguments);
        this.update_cp();
    },
    // Updates the control panel and render the elements that have yet to be rendered
    update_cp: function() {
        if (!this.$buttons) {
            this.renderButtons();
        }
        var status = {
            cp_content: {
                $buttons: this.$buttons,
                $searchview_buttons: this.$searchview_buttons,
                $pager: this.$pager,
                $searchview: this.$searchview,
            },
        };
        return this.updateControlPanel(status, {clear: true});
    },
    reload: function() {
        var self = this;
        return this._rpc({
                model: this.report_model,
                method: 'get_report_informations',
                args: [self.financial_id, self.report_options],
                context: self.odoo_context,
            })
            .then(function(result){
                self.parse_reports_informations(result);
                return self.render();
            });
    },
    render: function() {
        var self = this;
        this.render_template();
        this.render_footnotes();
        this.render_searchview_buttons();
        this.update_cp();
        this.$('.js_account_report_foldable').each(function() {
            if(!$(this).data('unfolded')) {
                self.fold($(this));
            }
        });
    },
    render_template: function() {
        this.$('.o_content').html(this.main_html);
        this.$('.o_content').find('.o_account_reports_summary_edit').hide();
        this.$('[data-toggle="tooltip"]').tooltip();
        this._add_line_classes();
    },
    _add_line_classes: function() {
        /* Pure JS to improve performance in very cornered case (~200k lines)
         * Jquery code:
         *  this.$('.o_account_report_line').filter(function () {
         *      return $(this).data('unfolded') === 'True';
         *  }).parent().addClass('o_js_account_report_parent_row_unfolded');
         */
        var el = this.$el[0];
        var report_lines = el.getElementsByClassName('o_account_report_line');
        for (var l=0; l < report_lines.length; l++) {
            var line = report_lines[l];
            var unfolded = line.dataset.unfolded;
            if (unfolded === 'True') {
                line.parentNode.classList.add('o_js_account_report_parent_row_unfolded');
            }
        }
        // This selector is not adaptable in pure JS
        this.$('tr[data-parent-id]').addClass('o_js_account_report_inner_row');
     },
    filter_accounts: function(e) {
        var self = this;
        var query = e.target.value.trim().toLowerCase();
        this.filterOn = false;
        this.$('.o_account_reports_level2').each(function(index, el) {
            var $accountReportLineFoldable = $(el);
            var line_id = $accountReportLineFoldable.find('.o_account_report_line').data('id');
            var $childs = self.$('tr[data-parent-id="'+line_id+'"]');
            var lineText = $accountReportLineFoldable.find('.account_report_line_name')
                // Only the direct text node, not text situated in other child nodes
                .contents().get(0).nodeValue
                .trim();

            // The python does this too
            var queryFound = lineText.split(' ').some(function (str) {
                return str.toLowerCase().startsWith(query);
            });

            $accountReportLineFoldable.toggleClass('o_account_reports_filtered_lines', !queryFound);
            $childs.toggleClass('o_account_reports_filtered_lines', !queryFound);

            if (!queryFound) {
                self.filterOn = true;
            }
        });
        if (this.filterOn) {
            this.$('.o_account_reports_level1.total').hide();
        }
        else {
            this.$('.o_account_reports_level1.total').show();
        }
        this.report_options['filter_accounts'] = query;
        this.render_footnotes();
    },
    selected_column: function(e) {
        var self = this;
        if (self.report_options.selected_column !== undefined) {
            var col_number = Array.prototype.indexOf.call(e.currentTarget.parentElement.children, e.currentTarget) + 1; // we can't have negative 0 so lets start index at 1
            if (self.report_options.selected_column && self.report_options.selected_column == col_number) {
                self.report_options.selected_column = -col_number;
            } else {
                self.report_options.selected_column = col_number;
            }
            self.reload()
        }
    },
    _onChangeExpectedDate: function (event) {
        var self = this;
        var targetID = parseInt($(event.target).attr('data-id'));
        var parentID = parseInt($(event.target).attr('parent-id').split("_")[1]);
        var $content = $(QWeb.render("paymentDateForm", {target_id: targetID}));
        var paymentDatePicker = new datepicker.DateWidget(this);
        paymentDatePicker.appendTo($content.find('div.o_account_reports_payment_date_picker'));
        var save = function () {
            return this._rpc({
                model: 'res.partner',
                method: 'change_expected_date',
                args: [[parentID], {
                    move_line_id: parseInt($content.find("#target_id").val()),
                    expected_pay_date: paymentDatePicker.getValue(),
                }],
            }).then(function() {
                self.reload();
            });
        };
        new Dialog(this, {
            title: 'Odoo',
            size: 'medium',
            $content: $content,
            buttons: [{
                text: _t('Save'),
                classes: 'btn-primary',
                close: true,
                click: save
            },
            {
                text: _t('Cancel'),
                close: true
            }]
        }).open();
    },
    render_searchview_buttons: function() {
        var self = this;
        // bind searchview buttons/filter to the correct actions
        var $datetimepickers = this.$searchview_buttons.find('.js_account_reports_datetimepicker');
        var options = { // Set the options for the datetimepickers
            locale : moment.locale(),
            format : 'L',
            icons: {
                date: "fa fa-calendar",
            },
        };
        // attach datepicker
        $datetimepickers.each(function () {
            var name = $(this).find('input').attr('name');
            var defaultValue = $(this).data('default-value');
            $(this).datetimepicker(options);
            var dt = new datepicker.DateWidget(options);
            dt.replace($(this)).then(function () {
                dt.$el.find('input').attr('name', name);
                if (defaultValue) { // Set its default value if there is one
                    dt.setValue(moment(defaultValue));
                }
            });
        });
        // format date that needs to be show in user lang
        _.each(this.$searchview_buttons.find('.js_format_date'), function(dt) {
            var date_value = $(dt).html();
            $(dt).html((new moment(date_value)).format('ll'));
        });
        // fold all menu
        this.$searchview_buttons.find('.js_foldable_trigger').click(function (event) {
            $(this).toggleClass('o_closed_menu o_open_menu');
            self.$searchview_buttons.find('.o_foldable_menu[data-filter="'+$(this).data('filter')+'"]').toggleClass('o_closed_menu');
        });
        // render filter (add selected class to the options that are selected)
        _.each(self.report_options, function(k) {
            if (k!== null && k.filter !== undefined) {
                self.$searchview_buttons.find('[data-filter="'+k.filter+'"]').addClass('selected');
            }
        });
        _.each(this.$searchview_buttons.find('.js_account_report_bool_filter'), function(k) {
            $(k).toggleClass('selected', self.report_options[$(k).data('filter')]);
        });
        _.each(this.$searchview_buttons.find('.js_account_report_choice_filter'), function(k) {
            $(k).toggleClass('selected', (_.filter(self.report_options[$(k).data('filter')], function(el){return ''+el.id == ''+$(k).data('id') && el.selected === true;})).length > 0);
        });
        $('.js_account_report_group_choice_filter', this.$searchview_buttons).each(function (i, el) {
            var $el = $(el);
            var ids = $el.data('member-ids');
            $el.toggleClass('selected', _.every(self.report_options[$el.data('filter')], function (member) {
                // only look for actual ids, discard separators and section titles
                if(typeof member.id == 'number'){
                  // true if selected and member or non member and non selected
                  return member.selected === (ids.indexOf(member.id) > -1);
                } else {
                  return true;
                }
            }));
        });
        _.each(this.$searchview_buttons.find('.js_account_reports_one_choice_filter'), function(k) {
            $(k).toggleClass('selected', ''+self.report_options[$(k).data('filter')] === ''+$(k).data('id'));
        });
        // click events
        this.$searchview_buttons.find('.js_account_report_date_filter').click(function (event) {
            self.report_options.date.filter = $(this).data('filter');
            var error = false;
            if ($(this).data('filter') === 'custom') {
                var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from"]');
                var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to"]');
                if (date_from.length > 0){
                    error = date_from.val() === "" || date_to.val() === "";
                    self.report_options.date.date_from = field_utils.parse.date(date_from.val());
                    self.report_options.date.date_to = field_utils.parse.date(date_to.val());
                }
                else {
                    error = date_to.val() === "";
                    self.report_options.date.date_to = field_utils.parse.date(date_to.val());
                }
            }
            if (error) {
                new WarningDialog(self, {
                    title: _t("Odoo Warning"),
                }, {
                    message: _t("Date cannot be empty")
                }).open();
            } else {
                self.reload();
            }
        });
        this.$searchview_buttons.find('.js_account_report_bool_filter').click(function (event) {
            var option_value = $(this).data('filter');
            self.report_options[option_value] = !self.report_options[option_value];
            if (option_value === 'unfold_all') {
                self.unfold_all(self.report_options[option_value]);
            }
            self.reload();
        });
        $('.js_account_report_group_choice_filter', this.$searchview_buttons).click(function () {
            var option_value = $(this).data('filter');
            var option_member_ids = $(this).data('member-ids') || [];
            var is_selected = $(this).hasClass('selected');
            _.each(self.report_options[option_value], function (el) {
                // if group was selected, we want to uncheck all
                el.selected = !is_selected && (option_member_ids.indexOf(Number(el.id)) > -1);
            });
            self.reload();
        });
        this.$searchview_buttons.find('.js_account_report_choice_filter').click(function (event) {
            var option_value = $(this).data('filter');
            var option_id = $(this).data('id');
            _.filter(self.report_options[option_value], function(el) {
                if (''+el.id == ''+option_id){
                    if (el.selected === undefined || el.selected === null){el.selected = false;}
                    el.selected = !el.selected;
                } else if (option_value === 'ir_filters') {
                    el.selected = false;
                }
                return el;
            });
            self.reload();
        });
        this.$searchview_buttons.find('.js_account_reports_one_choice_filter').click(function (event) {
            self.report_options[$(this).data('filter')] = $(this).data('id');
            self.reload();
        });
        this.$searchview_buttons.find('.js_account_report_date_cmp_filter').click(function (event) {
            self.report_options.comparison.filter = $(this).data('filter');
            var error = false;
            var number_period = $(this).parent().find('input[name="periods_number"]');
            self.report_options.comparison.number_period = (number_period.length > 0) ? parseInt(number_period.val()) : 1;
            if ($(this).data('filter') === 'custom') {
                var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from_cmp"]');
                var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to_cmp"]');
                if (date_from.length > 0) {
                    error = date_from.val() === "" || date_to.val() === "";
                    self.report_options.comparison.date_from = field_utils.parse.date(date_from.val());
                    self.report_options.comparison.date_to = field_utils.parse.date(date_to.val());
                }
                else {
                    error = date_to.val() === "";
                    self.report_options.comparison.date_to = field_utils.parse.date(date_to.val());
                }
            }
            if (error) {
                new WarningDialog(self, {
                    title: _t("Odoo Warning"),
                }, {
                    message: _t("Date cannot be empty")
                }).open();
            } else {
                self.reload();
            }
        });

        // partner filter
        if (this.report_options.partner) {
            if (!this.M2MFilters) {
                var fields = {};
                if ('partner_ids' in this.report_options) {
                    fields['partner_ids'] = {
                        label: _t('Partners'),
                        modelName: 'res.partner',
                        value: this.report_options.partner_ids.map(Number),
                    };
                }
                if ('partner_categories' in this.report_options) {
                    fields['partner_categories'] = {
                        label: _t('Tags'),
                        modelName: 'res.partner.category',
                        value: this.report_options.partner_categories.map(Number),
                    };
                }
                if (!_.isEmpty(fields)) {
                    this.M2MFilters = new M2MFilters(this, fields);
                    this.M2MFilters.appendTo(this.$searchview_buttons.find('.js_account_partner_m2m'));
                }
            } else {
                this.$searchview_buttons.find('.js_account_partner_m2m').append(this.M2MFilters.$el);
            }
        }

        // analytic filter
        if (this.report_options.analytic) {
            if (!this.M2MFilters) {
                var fields = {};
                if (this.report_options.analytic_accounts) {
                    fields['analytic_accounts'] = {
                        label: _t('Accounts'),
                        modelName: 'account.analytic.account',
                        value: this.report_options.analytic_accounts.map(Number),
                    };
                }
                if (this.report_options.analytic_tags) {
                    fields['analytic_tags'] = {
                        label: _t('Tags'),
                        modelName: 'account.analytic.tag',
                        value: this.report_options.analytic_tags.map(Number),
                    };
                }
                if (!_.isEmpty(fields)) {
                    this.M2MFilters = new M2MFilters(this, fields);
                    this.M2MFilters.appendTo(this.$searchview_buttons.find('.js_account_analytic_m2m'));
                }
            } else {
                this.$searchview_buttons.find('.js_account_analytic_m2m').append(this.M2MFilters.$el);
            }
        }
    },
    format_date: function(moment_date) {
        var date_format = 'YYYY-MM-DD';
        return moment_date.format(date_format);
    },
    renderButtons: function() {
        var self = this;
        this.$buttons = $(QWeb.render("accountReports.buttons", {buttons: this.buttons}));
        // bind actions
        _.each(this.$buttons.siblings('button'), function(el) {
            $(el).click(function() {
                self.$buttons.attr('disabled', true);
                return self._rpc({
                        model: self.report_model,
                        method: $(el).attr('action'),
                        args: [self.financial_id, self.report_options],
                        context: self.odoo_context,
                    })
                    .then(function(result){
                        var doActionProm = self.do_action(result);
                        self.$buttons.attr('disabled', false);
                        return doActionProm;
                    })
                    .guardedCatch(function() {
                        self.$buttons.attr('disabled', false);
                    });
            });
        });
        return this.$buttons;
    },
    edit_summary: function(e) {
        var $textarea = $(e.target).parents('.o_account_reports_body').find('textarea[name="summary"]');
        var height = Math.max($(e.target).parents('.o_account_reports_body').find('.o_account_report_summary').height(), 100); // Compute the height that will be needed
        // TODO master: remove replacing <br /> (this was kept for existing data)
        var text = $textarea.val().replace(new RegExp('<br />', 'g'), '\n'); // Remove unnecessary spaces and line returns
        $textarea.height(height); // Give it the right height
        $textarea.val(text);
        $(e.target).parents('.o_account_reports_body').find('.o_account_reports_summary_edit').show();
        $(e.target).parents('.o_account_reports_body').find('.o_account_reports_summary').hide();
        $(e.target).parents('.o_account_reports_body').find('textarea[name="summary"]').focus();
    },
    save_summary: function(e) {
        var self = this;
        var text = $(e.target).siblings().val().replace(/[ \t]+/g, ' ');
        return this._rpc({
                model: 'account.report.manager',
                method: 'write',
                args: [this.report_manager_id, {summary: text}],
                context: this.odoo_context,
            })
            .then(function(result){
                self.$el.find('.o_account_reports_summary_edit').hide();
                self.$el.find('.o_account_reports_summary').show();
                if (!text) {
                    var $content = $("<input type='text' class='o_input' name='summary'/>");
                    $content.attr('placeholder', _t('Add a note'));
                } else {
                    var $content = $('<span />').text(text).html(function (i, value) {
                        return value.replace(/\n/g, '<br>');
                    });
                }
                return $(e.target).parent().siblings('.o_account_reports_summary').find('> .o_account_report_summary').html($content);
            });
    },
    render_footnotes: function() {
        var self = this;
        // First assign number based on visible lines
        var $dom_footnotes = self.$el.find('.js_account_report_line_footnote:not(.folded)');
        $dom_footnotes.html('');
        var number = 1;
        var footnote_to_render = [];
        _.each($dom_footnotes, function(el) {
            if ($(el).parents('.o_account_reports_filtered_lines').length > 0) {
                return;
            }
            var line_id = $(el).data('id');
            var footnote = _.filter(self.footnotes, function(footnote) {return ''+footnote.line === ''+line_id;});
            if (footnote.length !== 0) {
                $(el).html('<sup><b class="o_account_reports_footnote_sup"><a href="#footnote'+number+'">'+number+'</a></b></sup>');
                footnote[0].number = number;
                number += 1;
                footnote_to_render.push(footnote[0]);
            }
        });
        // Render footnote template
        return this._rpc({
                model: this.report_model,
                method: 'get_html_footnotes',
                args: [self.financial_id, footnote_to_render],
                context: self.odoo_context,
            })
            .then(function(result){
                return self.$el.find('.js_account_report_footnotes').html(result);
            });
    },
    add_edit_footnote: function(e) {
        // open dialog window with either empty content or the footnote text value
        var self = this;
        var line_id = $(e.target).data('id');
        // check if we already have some footnote for this line
        var existing_footnote = _.filter(self.footnotes, function(footnote) {
            return ''+footnote.line === ''+line_id;
        });
        var text = '';
        if (existing_footnote.length !== 0) {
            text = existing_footnote[0].text;
        }
        var $content = $(QWeb.render('accountReports.footnote_dialog', {text: text, line: line_id}));
        var save = function() {
            var footnote_text = $('.js_account_reports_footnote_note').val().replace(/[ \t]+/g, ' ');
            if (!footnote_text && existing_footnote.length === 0) {return;}
            if (existing_footnote.length !== 0) {
                if (!footnote_text) {
                    return self.$el.find('.footnote[data-id="'+existing_footnote[0].id+'"] .o_account_reports_footnote_icons').click();
                }
                // replace text of existing footnote
                return this._rpc({
                        model: 'account.report.footnote',
                        method: 'write',
                        args: [existing_footnote[0].id, {text: footnote_text}],
                        context: this.odoo_context,
                    })
                    .then(function(result){
                        _.each(self.footnotes, function(footnote) {
                            if (footnote.id === existing_footnote[0].id){
                                footnote.text = footnote_text;
                            }
                        });
                        return self.render_footnotes();
                    });
            }
            else {
                // new footnote
                return this._rpc({
                        model: 'account.report.footnote',
                        method: 'create',
                        args: [{line: line_id, text: footnote_text, manager_id: self.report_manager_id}],
                        context: this.odoo_context,
                    })
                    .then(function(result){
                        self.footnotes.push({id: result, line: line_id, text: footnote_text});
                        return self.render_footnotes();
                    });
            }
        };
        new Dialog(this, {title: 'Annotate', size: 'medium', $content: $content, buttons: [{text: 'Save', classes: 'btn-primary', close: true, click: save}, {text: 'Cancel', close: true}]}).open();
    },
    delete_footnote: function(e) {
        var self = this;
        var footnote_id = $(e.target).parents('.footnote').data('id');
        return this._rpc({
                model: 'account.report.footnote',
                method: 'unlink',
                args: [footnote_id],
                context: this.odoo_context,
            })
            .then(function(result){
                // remove footnote from report_information
                self.footnotes = _.filter(self.footnotes, function(element) {
                    return element.id !== footnote_id;
                });
                return self.render_footnotes();
            });
    },
    fold_unfold: function(e) {
        var self = this;
        if ($(e.target).hasClass('caret') || $(e.target).parents('.o_account_reports_footnote_sup').length > 0){return;}
        e.stopPropagation();
        e.preventDefault();
        var line = $(e.target).parents('td');
        if (line.length === 0) {line = $(e.target);}
        var method = line.data('unfolded') === 'True' ? this.fold(line) : this.unfold(line);
        Promise.resolve(method).then(function() {
            self.render_footnotes();
            self.persist_options();
        });
    },
    fold: function(line) {
        var self = this;
        var line_id = line.data('id');
        line.find('.fa-caret-down').toggleClass('fa-caret-right fa-caret-down');
        line.toggleClass('folded');
        $(line).parent('tr').removeClass('o_js_account_report_parent_row_unfolded');
        var $lines_to_hide = this.$el.find('tr[data-parent-id="'+line_id+'"]');
        var index = self.report_options.unfolded_lines.indexOf(line_id);
        if (index > -1) {
            self.report_options.unfolded_lines.splice(index, 1);
        }
        if ($lines_to_hide.length > 0) {
            line.data('unfolded', 'False');
            $lines_to_hide.find('.js_account_report_line_footnote').addClass('folded');
            $lines_to_hide.hide();
            _.each($lines_to_hide, function(el){
                var child = $(el).find('[data-id]:first');
                if (child) {
                    self.fold(child);
                }
            })
        }
        return false;
    },
    unfold: function(line) {
        var self = this;
        var line_id = line.data('id');
        line.toggleClass('folded');
        self.report_options.unfolded_lines.push(line_id);
        var $lines_in_dom = this.$el.find('tr[data-parent-id="'+line_id+'"]');
        if ($lines_in_dom.length > 0) {
            $lines_in_dom.find('.js_account_report_line_footnote').removeClass('folded');
            $lines_in_dom.show();
            line.find('.fa-caret-right').toggleClass('fa-caret-right fa-caret-down');
            line.data('unfolded', 'True');
            this._add_line_classes();
            return true;
        }
        else {
            return this._rpc({
                    model: this.report_model,
                    method: 'get_html',
                    args: [self.financial_id, self.report_options, line.data('id')],
                    context: self.odoo_context,
                })
                .then(function(result){
                    $(line).parent('tr').replaceWith(result);
                    self._add_line_classes();
                });
        }
    },
    load_more: function (ev) {
        var $line = $(ev.target).parents('td');
        var id = $line.data('id');
        var offset = $line.data('offset') || 0;
        var progress = $line.data('progress') || 0;
        var remaining = $line.data('remaining') || 0;
        var options = _.extend({}, this.report_options, {lines_offset: offset, lines_progress: progress, lines_remaining: remaining});
        var self = this;
        this._rpc({
                model: this.report_model,
                method: 'get_html',
                args: [this.financial_id, options, id],
                context: this.odoo_context,
            })
            .then(function (result){
                var $tr = $line.parents('.o_account_reports_load_more');
                $tr.after(result);
                $tr.remove();
                self._add_line_classes();
            });
    },
    unfold_all: function(bool) {
        var self = this;
        var lines = this.$el.find('.js_account_report_foldable');
        self.report_options.unfolded_lines = [];
        if (bool) {
            _.each(lines, function(el) {
                self.report_options.unfolded_lines.push($(el).data('id'));
            });
        }
    },
    trigger_action: function(e) {
        e.stopPropagation();
        var self = this;
        var action = $(e.target).attr('action');
        var id = $(e.target).parents('td').data('id');
        var params = $(e.target).data();
        var context = new Context(this.odoo_context, params.actionContext || {}, {active_id: id});

        params = _.omit(params, 'actionContext');
        if (action) {
            return this._rpc({
                    model: this.report_model,
                    method: action,
                    args: [this.financial_id, this.report_options, params],
                    context: context.eval(),
                })
                .then(function(result){
                    return self.do_action(result);
                });
        }
    },
});

core.action_registry.add('account_report', accountReportsWidget);

return accountReportsWidget;

});
