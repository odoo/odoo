odoo.define('portal.portal', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
const Dialog = require('web.Dialog');
const {_t, qweb} = require('web.core');
const session = require('web.session');

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '.o_portal_details',
    events: {
        'change select[name="country_id"]': '_onCountryChange',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        this.$state = this.$('select[name="state_id"]');
        this.$stateOptions = this.$state.filter(':enabled').find('option:not(:first)');
        this._adaptAddressForm();

        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptAddressForm: function () {
        var $country = this.$('select[name="country_id"]');
        var countryID = ($country.val() || 0);
        this.$stateOptions.detach();
        var $displayedState = this.$stateOptions.filter('[data-country_id=' + countryID + ']');
        var nb = $displayedState.appendTo(this.$state).show().length;
        this.$state.parent().toggle(nb >= 1);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCountryChange: function () {
        this._adaptAddressForm();
    },
});

publicWidget.registry.PortalHomeCounters = publicWidget.Widget.extend({
    selector: '.o_portal_my_home',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this._updateCounters();
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return a list of counters name linked to a line that we want to keep
     * regardless of the number of documents present
     * @private
     * @returns {Array}
     */
    _getCountersAlwaysDisplayed() {
        return [];
    },

    /**
     * @private
     */
    async _updateCounters(elem) {
        const numberRpc = 3;
        const needed = Object.values(this.el.querySelectorAll('[data-placeholder_count]'))
                                .map(documentsCounterEl => documentsCounterEl.dataset['placeholder_count']);
        const counterByRpc = Math.ceil(needed.length / numberRpc);  // max counter, last can be less
        const countersAlwaysDisplayed = this._getCountersAlwaysDisplayed();

        const proms = [...Array(Math.min(numberRpc, needed.length)).keys()].map(async i => {
            const documentsCountersData = await this._rpc({
                route: "/my/counters",
                params: {
                    counters: needed.slice(i * counterByRpc, (i + 1) * counterByRpc)
                },
            });
            Object.keys(documentsCountersData).forEach(counterName => {
                const documentsCounterEl = this.el.querySelector(`[data-placeholder_count='${counterName}']`);
                documentsCounterEl.textContent = documentsCountersData[counterName];
                // The element is hidden by default, only show it if its counter is > 0 or if it's in the list of counters always shown
                if (documentsCountersData[counterName] !== 0 || countersAlwaysDisplayed.includes(counterName)) {
                    documentsCounterEl.parentElement.classList.remove('d-none');
                }
            });
            return documentsCountersData;
        });
        return Promise.all(proms).then((results) => {
            const counters = results.reduce((prev, current) => Object.assign({...prev, ...current}), {});
            this.el.querySelector('.o_portal_doc_spinner').remove();
            // Display a message when there are no documents available if there are no counters > 0 and no counters always shown
            if (!countersAlwaysDisplayed.length && !Object.values(counters).filter((val) => val > 0).length) {
                this.el.querySelector('.o_portal_no_doc_message').classList.remove('d-none');
            }
        });
    },
});

publicWidget.registry.portalSearchPanel = publicWidget.Widget.extend({
    selector: '.o_portal_search_panel',
    events: {
        'click .dropdown-item': '_onDropdownItemClick',
        'submit': '_onSubmit',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this._adaptSearchLabel(this.$('.dropdown-item.active'));
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptSearchLabel: function (elem) {
        var $label = $(elem).clone();
        $label.find('span.nolabel').remove();
        this.$('input[name="search"]').attr('placeholder', $label.text().trim());
    },
    /**
     * @private
     */
    _search: function () {
        var search = $.deparam(window.location.search.substring(1));
        search['search_in'] = this.$('.dropdown-item.active').attr('href').replace('#', '');
        search['search'] = this.$('input[name="search"]').val();
        window.location.search = $.param(search);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDropdownItemClick: function (ev) {
        ev.preventDefault();
        var $item = $(ev.currentTarget);
        $item.closest('.dropdown-menu').find('.dropdown-item').removeClass('active');
        $item.addClass('active');

        this._adaptSearchLabel(ev.currentTarget);
    },
    /**
     * @private
     */
    _onSubmit: function (ev) {
        ev.preventDefault();
        this._search();
    },
});

publicWidget.registry.NewAPIKeyButton = publicWidget.Widget.extend({
    selector: '.o_portal_new_api_key',
    events: {
        click: '_onClick'
    },

    async _onClick(e){
        e.preventDefault();
        // This call is done just so it asks for the password confirmation before starting displaying the
        // dialog forms, to mimic the behavior from the backend, in which it asks for the password before
        // displaying the wizard.
        // The result of the call is unused. But it's required to call a method with the decorator `@check_identity`
        // in order to use `handleCheckIdentity`.
        await handleCheckIdentity(this.proxy('_rpc'), this._rpc({
            model: 'res.users',
            method: 'api_key_wizard',
            args: [session.user_id],
        }));
        const self = this;
        const d_description = new Dialog(self, {
            title: _t('New API Key'),
            $content: qweb.render('portal.keydescription'),
            buttons: [{text: _t('Confirm'), classes: 'btn-primary', close: true, click: async () => {
                var description = d_description.el.querySelector('[name="description"]').value;
                var wizard_id = await this._rpc({
                    model: 'res.users.apikeys.description',
                    method: 'create',
                    args: [{name: description}],
                });
                var res = await handleCheckIdentity(
                    this.proxy('_rpc'),
                    this._rpc({
                        model: 'res.users.apikeys.description',
                        method: 'make_key',
                        args: [wizard_id],
                    })
                );
                const d_show = new Dialog(self, {
                    title: _t('API Key Ready'),
                    $content: qweb.render('portal.keyshow', {key: res.context.default_key}),
                    buttons: [{text: _t('Close'), clases: 'btn-primary', close: true}],
                });
                d_show.on('closed', this, () => {
                    window.location = window.location;
                });
                d_show.open();
            }}, {text: _t('Discard'), close: true}],
        });
        d_description.opened(() => {
            const input = d_description.el.querySelector('[name="description"]');
            input.focus();
            d_description.el.addEventListener('submit', (e) => {
                e.preventDefault();
                d_description.$footer.find('.btn-primary').click();
            });
        });
        d_description.open();
    }
});

publicWidget.registry.RemoveAPIKeyButton = publicWidget.Widget.extend({
    selector: '.o_portal_remove_api_key',
    events: {
        click: '_onClick'
    },

    async _onClick(e){
        e.preventDefault();
        await handleCheckIdentity(
            this.proxy('_rpc'),
            this._rpc({
                model: 'res.users.apikeys',
                method: 'remove',
                args: [parseInt(this.target.id)]
            })
        );
        window.location = window.location;
    }
});

publicWidget.registry.portalSecurity = publicWidget.Widget.extend({
    selector: '.o_portal_security_body',

    /**
     * @override
     */
    init: function () {
        // Show the "deactivate your account" modal if needed
        $('.modal.show#portal_deactivate_account_modal').removeClass('d-block').modal('show');

        // Remove the error messages when we close the modal,
        // so when we re-open it again we get a fresh new form
        $('.modal#portal_deactivate_account_modal').on('hide.bs.modal', (event) => {
            const $target = $(event.currentTarget);
            $target.find('.alert').remove();
            $target.find('.invalid-feedback').remove();
            $target.find('.is-invalid').removeClass('is-invalid');
        });

        return this._super(...arguments);
    },

});

/**
 * Wraps an RPC call in a check for the result being an identity check action
 * descriptor. If no such result is found, just returns the wrapped promise's
 * result as-is; otherwise shows an identity check dialog and resumes the call
 * on success.
 *
 * Warning: does not in and of itself trigger an identity check, a promise which
 * never triggers and identity check internally will do nothing of use.
 *
 * @param {Function} rpc Widget#_rpc bound do the widget
 * @param {Promise} wrapped promise to check for an identity check request
 * @returns {Promise} result of the original call
 */
function handleCheckIdentity(rpc, wrapped) {
    return wrapped.then((r) => {
        if (!_.isMatch(r, {type: 'ir.actions.act_window', res_model: 'res.users.identitycheck'})) {
            return r;
        }
        const check_id = r.res_id;
        return new Promise((resolve, reject) => {
            const d = new Dialog(null, {
                title: _t("Security Control"),
                $content: qweb.render('portal.identitycheck'),
                buttons: [{
                    text: _t("Confirm Password"), classes: 'btn btn-primary',
                    // nb: if click & close, waits for click to resolve before closing
                    click() {
                        const password_input = this.el.querySelector('[name=password]');
                        if (!password_input.reportValidity()) {
                            password_input.classList.add('is-invalid');
                            return;
                        }
                        return rpc({
                            model: 'res.users.identitycheck',
                            method: 'write',
                            args: [check_id, {password: password_input.value}]
                        }).then(() => rpc({
                            model: 'res.users.identitycheck',
                            method: 'run_check',
                            args: [check_id]
                        })).then((r) => {
                            this.close();
                            resolve(r);
                        }, (err) => {
                            err.event.preventDefault(); // suppress crashmanager
                            password_input.classList.add('is-invalid');
                            password_input.setCustomValidity(_t("Check failed"));
                            password_input.reportValidity();
                        });
                    }
                }, {
                    text: _t('Cancel'), close: true
                }]
            }).on('close', null, () => {
                // unlink wizard object?
                reject();
            });
            d.opened(() => {
                const pw = d.el.querySelector('[name="password"]');
                pw.focus();
                pw.addEventListener('input', () => {
                    pw.classList.remove('is-invalid');
                    pw.setCustomValidity('');
                });
                d.el.addEventListener('submit', (e) => {
                    e.preventDefault();
                    d.$footer.find('.btn-primary').click();
                });
            });
            d.open();
        });
    });
}
return {
    handleCheckIdentity,
}
});
