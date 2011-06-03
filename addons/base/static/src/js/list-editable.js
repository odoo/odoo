/**
 * @namespace handles editability case for lists, because it depends on form and forms already depends on lists it had to be split out
 */
openerp.base.list.editable = function (openerp) {
    // editability status of list rows
    openerp.base.ListView.prototype.defaults.editable = null;

    var old_actual_search = openerp.base.ListView.prototype.do_actual_search;
    _.extend(openerp.base.ListView.prototype, {
        /**
         * Sets editability status for the list, based on defaults, view
         * architecture and the provided flag, if any.
         *
         * @param {Boolean} [force] forces the list to editability. Sets new row edition status to "bottom".
         */
        set_editable: function (force) {
            // If ``force``, set editability to bottom
            // else if editability flag in view arch, use that
            // otherwise rely on view default
            this.options.editable = (
                    (force && "bottom")
                    || this.fields_view.arch.attrs.editable
                    || this.defaults.editable);
        },
        /**
         * Replace do_actual_search to handle editability process
         */
        do_actual_search: function (results) {
            this.set_editable(results.context['set_editable']);
            old_actual_search.call(this, results);
        }
    });

    var old_list_row_clicked = openerp.base.ListView.List.prototype.row_clicked;
    _.extend(openerp.base.ListView.List.prototype, {
        row_clicked: function (event, index) {
            if (!this.options.editable) {
                return old_list_row_clicked.call(this, event, index);
            }
            this.render_row_as_form(index, event.currentTarget);
        },
        render_row_as_form: function (row_num, row) {
            var $new_row = $('<tr>', {
                    id: _.uniqueId('oe-editable-row-'),
                    'class': $(row).attr('class'),
                    onclick: function (e) {e.stopPropagation();}
                }).replaceAll(row);
            var editable_row_form = new openerp.base.FormView(
                    null, this.group.view.session, $new_row.attr('id'),
                    this.dataset, false);
            editable_row_form.template = 'ListView.row.form';
            editable_row_form.on_loaded({fields_view: this.get_fields_view()});
            editable_row_form.on_record_loaded.add({
                position: 'last',
                unique: true,
                callback: function () {
                    editable_row_form.$element.find('td')
                        // remove tr, tbody, table
                        .unwrap().unwrap().unwrap()
                        .removeAttr('width');
                }
            });
            editable_row_form.do_show();
        }
    });
};
