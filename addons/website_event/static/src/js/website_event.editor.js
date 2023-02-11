odoo.define('website_event.editor', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var time = require('web.time');
var WebsiteNewMenu = require('website.newMenu');
var _t = core._t;

var EventCreateDialog = Dialog.extend({
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(['/website_event/static/src/xml/event_create.xml']),
    template: 'website_event.event_create_dialog',
    events: _.extend({}, Dialog.prototype.events, {
        'change select[name="event_location"]': '_onLocationChanged',
        'click .input-group-append': '_onDatetimeClicked',
    }),
    jsLibs: [
        '/web/static/lib/daterangepicker/daterangepicker.js',
        '/web/static/src/legacy/js/libs/daterangepicker.js',
    ],
    

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("New Event"),
            size: 'medium',
            buttons: [
                {
                    text: _t("Create"),
                    classes: 'btn-primary',
                    click: this._onClickCreate.bind(this),
                },
                {
                    text: _t("Discard"),
                    close: true
                },
            ]
        });
        this.eventStart = moment();
        this.eventEnd = moment().add(1, "d");
        this._super(parent, options);
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(() => {
            // stat / end datetimes widgets
            self.$('input.daterange-input').each(function () {
                self._initDateRangePicker($(this));
            });
            // address select2 configuration
            self.$('input.o_wevent_js_address_id').select2(self._getSelect2AddressConfig());
        });
    },

    /**
     * @param {*} errors
     */
    _display_errors: function (errors) {
        this.$("p.text-danger").toggleClass('d-none', true);
        for (let i = 0; i < errors.length; i++) {
            this.$("#" + errors[i] + " p.text-danger").toggleClass('d-none', false);
        }
    },

    _getSelect2AddressConfig: function () {
        var self = this;
        return {
            allowClear: true,
            formatNoMatches: false,
            multiple: false,
            selection_data: false,
            width: '100%',

            createSearchChoice: function (name, data) {
                var addedPartner = $(this.opts.element).select2('data');
                if (_.filter(_.union(addedPartner, data), function (partner) {
                    return partner.text.toLowerCase().localeCompare(name.toLowerCase()) === 0;
                }).length === 0) {
                    return {
                        create: true,
                        id: _.uniqueId('address_'),
                        name: name,
                        text: _.str.sprintf(_t('Create "%s"'), name),
                    };
                }
            },
            fill_data: function (query, data) {
                var that = this;
                var partners = {results: []};
                _.each(data, function (partner) {
                    var contact_address = partner.contact_address.replace(/[\n]+/g, '').trim();
                    if (contact_address && that.matcher(query.term, contact_address)) {
                        partners.results.push({
                            id: partner.id,
                            text: contact_address,
                        });
                    }
                });
                query.callback(partners);
            },
            formatSelection: function (data) {
                if (data.name) {
                    data.text = data.name;
                }
                return data.text;
            },
            query: function (query) {
                var that = this;
                // fetch data only once and store it
                if (!this.selection_data) {
                    self._rpc({
                        model: 'res.partner',
                        method: 'search_read',
                        fields: ['contact_address'],
                        domain: [],
                    }).then(function (data) {
                        that.fill_data(query, data);
                        that.selection_data = data;
                    });
                } else {
                    this.fill_data(query, this.selection_data);
                }
            }
        }
    },

    _getSelect2AddressValues: function () {
        var select2Value = this.$('input.o_wevent_js_address_id').select2('data');
        if (select2Value) {
            if (select2Value.create) {
                return [0, {'name': select2Value.name}];
            } else {
                return [select2Value.id, {}];
            }
        }
        return [];
    },

    /**
     *
     * @param {*} $dateGroup
     */
    _initDateRangePicker: function ($dateGroup) {
        var minDate = moment().subtract(1, "d");
        var maxDate = moment().add(200, "y");
        var self = this;
        var textDirection = _t.database.parameters.direction;

        $dateGroup.daterangepicker({
            // dates
            endDate: this.eventEnd,
            maxDate: maxDate,
            minDate: minDate,
            startDate: this.eventStart,
            // display
            locale: {
                direction: textDirection,
                format: time.getLangDatetimeFormat().replace(':ss', ''),
                applyLabel: _t('Apply'),
                cancelLabel: _t('Cancel'),
                weekLabel: 'W',
                customRangeLabel: _t('Custom Range'),
                daysOfWeek: moment.weekdaysMin(),
                monthNames: moment.monthsShort(),
                firstDay: moment.localeData().firstDayOfWeek()
            },
            opens: 'left',
            timePicker: true,
            timePicker24Hour: true,
            viewDate: moment(new Date()).hours(minDate.hours()).minutes(minDate.minutes()).seconds(minDate.seconds()).milliseconds(minDate.milliseconds()),
        }, function (start, end, label) {
            self.eventStart = start;
            self.eventEnd = end;
        });
    },
    /**
     * @private
     */
    _prepareFormValues: function () {
        return {
            address_values: this._getSelect2AddressValues(),
            event_start: this.eventStart,
            event_end: this.eventEnd,
            location: this.$('select[name=event_location]').val(),
            name: this.$('input[name=name]').val().trim(),
        };
    },
    /**
     * @private
     * @param {*} values
     */
    _validateForm: function (values) {
        var errors = [];
        if (!values.name){
            errors.push('name');
        }
        if (values.location === 'on_site' && !values.address_values.length) {
            errors.push('address');
        }
        if (!values.event_start || !values.event_end) {
            errors.push('event_dates');
        }
        return errors;
    },

    /**
     * @private
     */
    _submitForm: function () {
        var self = this;
        var eventValues = this._prepareFormValues();
        var errors = this._validateForm(eventValues)
        console.log(eventValues, errors);
        if (errors.length) {
            this._display_errors(errors);
            return;
        }
        return this._rpc({
            route: '/event/add_event',
            params: eventValues,
        }).then((url) => {
            window.location.href = url;
            return new Promise(function () {});
        });
    },

    /**
     * @private
     */
    _onClickCreate: function () {
        return this._submitForm();
    },

    /**
     * @private
     * @param {*} ev
     */
    _onLocationChanged: function (ev) {
        this.$('.show_visibility_address').toggleClass('d-none', ev.target.value === 'online');
    },
});

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_event: '_createNewEvent',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new event to create, then creates it
     * and redirects the user to this new event.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewEvent: function () {
        var self = this;
        var def = new Promise(function (resolve) {
            var dialog = new EventCreateDialog(self, {});
            dialog.open();
            dialog.on('closed', self, resolve);
        });
        return def;
    },
});
});
