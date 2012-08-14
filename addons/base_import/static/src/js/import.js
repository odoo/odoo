openerp.base_import = function (instance) {
    var QWeb = instance.web.qweb;
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
            'change input.oe_import_file': 'file_update'
        },
        init: function (parent, dataset) {
            this._super(parent, {});
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

        //- File change section
        file_update: function (e) {
            if (!this.$('input.oe_import_file').val()) { return; }

            this.$element.removeClass('oe_import_preview oe_import_error');
            jsonp(this.$element, {
                url: '/base_import/set_file'
            }, this.proxy('file_updated'));
        },
        file_updated: function () {
            // immediately trigger preview...
            // TODO: test that write // succeeded?
            this.Import.call('parse_preview', [this.id, {
                quote: '"',
                separator: ',',
                headers: true,
            }]).then(this.proxy('preview'));
        },
        preview: function (result) {
            if (result.error) {
                this.$element.addClass('oe_import_error');
                this.$('.oe_import_error_report').html(
                    QWeb.render('ImportView.error', result));
            } else {
                this.$element.addClass('oe_import_preview');
                this.$('table').html(
                    QWeb.render('ImportView.preview', result));
            }
        },
    });
};
