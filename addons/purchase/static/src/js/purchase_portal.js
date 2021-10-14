odoo.define('purchase.portal', function (require) {
'use strict';

    var publicWidget = require('web.public.widget');
    const Dialog = require('web.Dialog');
    const {_t, qweb} = require('web.core');
    var portalAddress = publicWidget.registry.portalAddress;

    portalAddress.include({
        events: Object.assign({}, portalAddress.prototype.events, {
            'click .js_confirm_address': '_onClickConfirmAddress',
        }),
        xmlDependencies: (portalAddress.prototype.xmlDependencies || []).concat([
            '/purchase/static/src/xml/purchase_portal_warning_confirmation.xml',
        ]),

        _onClickConfirmAddress: async function (ev) {
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
                route: "/my/bank_account_warnings",
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
                        $content: qweb.render('purchase.purchase_portal_warning_confirmation', {
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
});
