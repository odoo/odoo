/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = publicWidget.Widget.extend({

    /**
     * @override
     */
    start: function () {
        var self = this;
        const post = this._getPost();
        const noTicketsOrdered = Object.values(post).map((value) => parseInt(value)).every(value => value === 0);
        var res = this._super.apply(this.arguments).then(function () {
            $('#registration_form .a-submit')
                .off('click')
                .click(function (ev) {
                    self.on_click(ev);
                })
                .prop('disabled', noTicketsOrdered);
        });
        return res;
    },

    _getPost: function () {
        var post = {};
        $('#registration_form select').each(function () {
            post[$(this).attr('name')] = $(this).val();
        });
        return post;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    on_click: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var $button = $(ev.currentTarget).closest('[type="submit"]');
        const post = this._getPost();
        $button.attr('disabled', true);
        return rpc($form.attr('action'), post).then(function (modal) {
            var $modal = $(modal);
            $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
            $modal.appendTo(document.body);
            const modalBS = new Modal($modal[0], {backdrop: 'static', keyboard: false});
            modalBS.show();
            $modal.appendTo('body').modal('show');
            $modal.on('click', '.js_goto_event', function () {
                $modal.modal('hide');
                $button.prop('disabled', false);
            });
            $modal.on('click', '.btn-close', function () {
                $button.prop('disabled', false);
            });
        });
    },
});

publicWidget.registry.EventRegistrationFormInstance = publicWidget.Widget.extend({
    selector: '#registration_form',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.instance = new EventRegistrationForm(this);
        return Promise.all([def, this.instance.attachTo(this.$el)]);
    },
    /**
     * @override
     */
    destroy: function () {
        this.instance.setElement(null);
        this._super.apply(this, arguments);
        this.instance.setElement(this.$el);
    },
});

publicWidget.registry.WebsiteEventLayout = publicWidget.Widget.extend({
    selector: '.o_wevent_index',
    disabledInEditableMode: false,
    events: {
        'change .o_wevent_apply_layout input': '_onApplyEventLayoutChange',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onApplyEventLayoutChange: function (ev) {
        const wysiwyg = this.options.wysiwyg;
        if (wysiwyg) {
            wysiwyg.odooEditor.observerUnactive('_onApplyEventLayoutChange');
        }
        var clickedValue = $(ev.target).val();
        if (!this.editableMode) {
            rpc('/event/save_event_layout_mode', {
                'layout_mode': clickedValue,
            });
        }

        const activeClasses = ev.target.parentElement.dataset.activeClasses.split(' ');
        ev.target.parentElement.querySelectorAll('.btn').forEach((btn) => {
            activeClasses.map(c => btn.classList.toggle(c));
        });

        // Toggle all css classes in order to switch between grid and list view
        var EventsIndexMainCol = document.querySelector('#o_wevent_index_main_col');
        EventsIndexMainCol.classList.toggle('opt_events_list_columns');
        EventsIndexMainCol.classList.toggle('opt_events_list_rows');

        var eventsGridElement = document.querySelector('#o_wevent_events_grid');
        const isSideNav = eventsGridElement.classList.contains('o_wevent_sidebar_enabled');

        let className = []
        if (clickedValue === 'grid') {
            if (isSideNav) {
                className = 'col-md-6';
            } else {
                className = 'col-md-6 col-lg-4 col-xl-3';
            }
        } else {
            if (isSideNav) {
                className = 'col-12';
            } else {
                className = 'col-xl-12';
            }
        }
        eventsGridElement.querySelectorAll('#o_wevent_event_main_div').forEach((eventDiv) => {
            eventDiv.className = className;
        });

        if (clickedValue === 'grid') {
            className = 'd-flex flex-wrap flex-column';
        } else {
            className = 'row mx-0';
        }
        eventsGridElement.querySelectorAll('#o_wevent_event_article_div').forEach((articleDiv) => {
            articleDiv.className = className;
        });

        eventsGridElement.querySelectorAll('header').forEach((header) => {
            header.classList.toggle('d-none');
        });

        eventsGridElement.querySelectorAll('.card-body').forEach((sidebar) => {
            sidebar.classList.toggle('d-none');
        });

        eventsGridElement.querySelectorAll('footer').forEach((footer) => {
            footer.classList.toggle('d-none');
        });

        if (wysiwyg) {
            wysiwyg.odooEditor.observerActive('_onApplyShopLayoutChange');
        }
    },
});

export default {
    EventRegistrationForm,
    WebsiteEventLayout: publicWidget.registry.WebsiteEventLayout,
};
