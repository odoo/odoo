odoo.define('portal.portal', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
const Dialog = require('web.Dialog');
const {_t, qweb} = require('web.core');
const ajax = require('web.ajax');

publicWidget.registry.portalAddress = publicWidget.Widget.extend({
    selector: '.o_portal_address',
    events: {
        'change select[name="country_id"]': '_onCountryChange',
        'click .js_confirm_main_address': '_onClickConfirmMainAddress',
    },
    xmlDependencies: [
        '/portal/static/src/xml/portal_address_warnings.xml',
    ],

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        this.$state = this.$('select[name="state_id"]');
        this.$stateOptions = this.$state.filter(':enabled').find('option:not(:first)');
        this._adaptAddressForm(this._getCountryId());

        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptAddressForm: function (countryID) {
        this.$stateOptions.detach();
        var $displayedState = this.$stateOptions.filter('[data-country_id=' + countryID + ']');
        var nb = $displayedState.appendTo(this.$state).show().length;
        this.$state.parent().toggle(nb >= 1);
    },

    /**
     * @private
     */
    _getCountryId: function () {
        var $country = this.$('select[name="country_id"]');
        return ($country.val() || 0);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCountryChange: function () {
        this._adaptAddressForm(this._getCountryId());
    },

    _onClickConfirmMainAddress: async function (ev) {
        ev.preventDefault();

        let form = $(ev.currentTarget.form);
        let data = form.serializeArray().reduce(function(data, {name, value}) {
            if (name in data) {
                if (Array.isArray(data[name])) {
                    data[name].append(value);
                } else {
                    data[name] = [data[name], value];
                }
            } else {
                data[name] = value;
            }
            return data;
        }, {});
        await this._rpc({
            route: "/my/main_address_confirmation_warnings",
            params: {
                data: data,
            },
        }).then(warnings => {
            if (!warnings.length) {
                form.submit();
            } else {
                warnings = warnings.map(warning => warning.split("\n"));
                let dialog = new Dialog(null, {
                    title: _t("Warning"),
                    size: 'medium',
                    $content: qweb.render('portal.portal_warning_confirmation', {
                        warnings: warnings, // format : each warning will be the item of a list, and can contain multiple lines (array of array of lines)
                    }),
                    buttons: [{
                        text: _t("PROCEED"), classes: 'btn btn-primary',
                        click() {
                            form.submit();
                        }
                    }, {
                        text: _t('CANCEL'), classes: 'btn btn-secondary', close: true
                    }]
                }).open();
            }
        });
    }
});

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '.o_portal_details',
    events: {
        'click .js_delete_address': '_onClickDeleteAddress',
    },

    _onClickDeleteAddress: function (ev) {
        ev.preventDefault();
        const confirmCallback = () => {
            $(ev.currentTarget.form).submit();
        };
        let dialog = Dialog.confirm(this, _t("Are you sure you want to delete this address?"), { confirm_callback: confirmCallback });
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
     * @private
     */
    async _updateCounters(elem) {
        const numberRpc = 3;
        const needed = this.$('[data-placeholder_count]')
                                .map((i, o) => $(o).data('placeholder_count'))
                                .toArray();
        const counterByRpc = Math.ceil(needed.length / numberRpc);  // max counter, last can be less

        const proms = [...Array(Math.min(numberRpc, needed.length)).keys()].map(async i => {
            await this._rpc({
                route: "/my/counters",
                params: {
                    counters: needed.slice(i * counterByRpc, (i + 1) * counterByRpc)
                },
            }).then(data => {
                Object.keys(data).map(k => this.$("[data-placeholder_count='" + k + "']").text(data[k]));
            });
        });
        return Promise.all(proms);
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
        return ajax.loadXML('/portal/static/src/xml/portal_security.xml', qweb).then(() => new Promise((resolve, reject) => {
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
        }));
    });
}
return {
    handleCheckIdentity,
}
});
