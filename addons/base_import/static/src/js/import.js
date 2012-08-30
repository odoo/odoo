openerp.base_import = function (instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var _lt = instance.web._lt;

    /**
     * Safari does not deal well at all with raw JSON data being
     * returned. As a result, we're going to cheat by using a
     * pseudo-jsonp: instead of getting JSON data in the iframe, we're
     * getting a ``script`` tag which consists of a function call and
     * the returned data (the json dump).
     *
     * The function is an auto-generated name bound to ``window``,
     * which calls back into the callback provided here.
     *
     * @param {Object} form the form element (DOM or jQuery) to use in the call
     * @param {Object} attributes jquery.form attributes object
     * @param {Function} callback function to call with the returned data
     */
    function jsonp(form, attributes, callback) {
        attributes = attributes || {};
        var options = {jsonp: _.uniqueId('import_callback_')};
        window[options.jsonp] = function () {
            delete window[options.jsonp];
            callback.apply(null, arguments);
        };
        if ('data' in attributes) {
            _.extend(attributes.data, options);
        } else {
            _.extend(attributes, {data: options});
        }
        _.extend(attributes, {
            dataType: 'script',
        });
        $(form).ajaxSubmit(attributes);
    }

    instance.web.DataImport = instance.web.Dialog.extend({
        template: 'ImportView',
        dialog_title: _lt("Import Data"),
        events: {
            'change input.oe_import_file': 'file_update',
            'click input.oe_import_has_header': function (e) {
                this.$el.toggleClass(
                    'oe_import_noheaders', !e.target.checked);
                this.settings_updated();
            },
            'click a.oe_import_csv': function (e) {
                e.preventDefault();
            },
            'click a.oe_import_export': function (e) {
                e.preventDefault();
            },
            'click dt a': function (e) {
                e.preventDefault();
                $(e.target).parent().next().toggle();
            }
        },
        init: function (parent, dataset) {
            var self = this;
            this._super(parent, {
                buttons: [
                    {text: _t("Import File"), click: function () {
                        self.do_import();
                    }, 'class': 'oe_import_dialog_button'}
                ]
            });
            this.res_model = parent.model;
            // import object id
            this.id = null;
            this.Import = new instance.web.Model('base_import.import');
        },
        start: function () {
            var self = this;
            return this.Import.call('create', [{
                'res_model': this.res_model
            }]).then(function (id) {
                self.id = id;
                self.$('input[name=import_id]').val(id);
            });
        },

        import_options: function () {
            return {
                // TODO: customizable gangnam style
                quote: '"',
                separator: ',',
                headers: this.$('input.oe_import_has_header').prop('checked'),
            };
        },

        //- File & settings change section
        file_update: function (e) {
            if (!this.$('input.oe_import_file').val()) { return; }

            this.$el.removeClass('oe_import_preview oe_import_error');
            jsonp(this.$el, {
                url: '/base_import/set_file'
            }, this.proxy('settings_updated'));
        },
        settings_updated: function () {
            this.$el.addClass('oe_import_with_file');
            // TODO: test that write // succeeded?
            this.Import.call(
                'parse_preview', [this.id, this.import_options()])
                .then(this.proxy('preview'));
        },
        preview: function (result) {
            if (result.error) {
                this.$el.addClass('oe_import_error');
                this.$('.oe_import_error_report').html(
                    QWeb.render('ImportView.preview.error', result));
            } else {
                this.$el.addClass('oe_import_preview');
                this.$('table').html(
                    QWeb.render('ImportView.preview', result));
            }
        },

        //- import itself
        do_import: function () {
            var fields = this.$('.oe_import_fields input').map(function (index, el) {
                return el.value || false;
            }).get();
            this.Import.call(
                'do', [this.id, fields, this.import_options()], {
                    // maybe could do a dryrun after successful
                    // preview or something (note: don't go to
                    // this.result if dryrun=true)
                    dryrun: false
                })
                .then(this.proxy('result'));
        },
        result: function (errors) {
            if (!errors.length) {
                if (this.getParent().reload_content) {
                    this.getParent().reload_content();
                }
                this.close();
                return;
            }
            // import failed (or maybe just warnings, if we ever get
            // warnings?)
            this.$el.addClass('oe_import_error');
            this.$('.oe_import_error_report').html(
                QWeb.render('ImportView.error', {errors: errors}));
        },
    });
};
