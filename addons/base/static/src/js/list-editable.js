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
            var self = this;
            var $new_row = $('<tr>', {
                    id: _.uniqueId('oe-editable-row-'),
                    'class': $(row).attr('class'),
                    onclick: function (e) {e.stopPropagation();}
                }).replaceAll(row)
                .keyup(function (e) {
                    if (e.which !== 13) {
                        return;
                    }
                    self.save_row(row_num, true);
                })
                .delegate('button.oe-list-save', 'click', function () {
                    self.save_row(row_num);
                });
            this.edition_form = _.extend(new openerp.base.FormView(
                    null, this.group.view.session, $new_row.attr('id'),
                    this.dataset, false), {
                template: 'ListView.row.form',
                registry: openerp.base.list.form.widgets
            });
            this.edition_form.on_loaded({fields_view: this.get_fields_view()});
            this.edition_form.on_record_loaded.add({
                position: 'last',
                unique: true,
                callback: function () {
                    self.edition_form.$element
                        .find('td')
                            .addClass('oe-field-cell')
                            .removeAttr('width')
                        .end()
                        .find('td:first').removeClass('oe-field-cell').end()
                        .find('td:last').removeClass('oe-field-cell').end();
                }
            });
            this.edition_form.do_show();
        },
        /**
         * Saves the current row, and triggers the edition of its following
         * sibling if asked.
         *
         * @param {Number} row_num the row to save
         * @param {Boolean} [edit_next=false] should the next row become editable
         */
        save_row: function (row_num, edit_next) {
            var self = this;
            this.edition_form.do_save(function () {
                // nuke form
                // re-render current row
                if (edit_next) {
                    // self.row_clicked({currentTarget: current_row.nextSibling}, row_num + 1)
                }
            });
        }
    });
    openerp.base.list = {form: {}};
    openerp.base.list.form.WidgetFrame = openerp.base.form.WidgetFrame.extend({
        template: 'ListView.row.frame'
    });
    var form_widgets = openerp.base.form.widgets;
    openerp.base.list.form.widgets = form_widgets.clone({
        'frame': 'openerp.base.list.form.WidgetFrame'
    });
    // All form widgets inherit a problematic behavior from
    // openerp.base.form.WidgetFrame: the cell itself is removed when invisible
    // whether it's @invisible or @attrs[invisible]. In list view, only the
    // former should completely remove the cell. We need to override update_dom
    // on all widgets since we can't just hit on widget itself (I think)
    var list_form_widgets = openerp.base.list.form.widgets;
    _(list_form_widgets.map).each(function (widget_path, key) {
        if (key === 'frame') { return; }
        var new_path = 'openerp.base.list.form.' + key;

        openerp.base.list.form[key] = (form_widgets.get_object(key)).extend({
            update_dom: function () {
                this.$element.children().css('visibility', '');
                if (this.invisible && this.node.attrs.invisible !== '1') {
                    this.$element.children().css('visibility', 'hidden');
                } else {
                    this._super();
                }
            }
        });
        list_form_widgets.add(key, new_path);
    });
};
