odoo.define('point_of_sale.res_config_settings', function (require) {
    'use strict';

    const ResConfigSettings = require('base.settings');

    ResConfigSettings.Renderer.include({
        _searchModule: function (module) {
            const isModuleVisible = this._super.apply(this, arguments);
            if (isModuleVisible && module.key === 'point_of_sale') {
                // Find all field elements (.o_field_widget) from shown (:not(.o_hidden)) setting boxes.
                // Then filter those with name attributes that starts with 'pos_'.
                const posConfigFields = module.settingView
                    .find('.o_setting_box:not(.o_hidden) div.o_field_widget')
                    .filter(function (_, el) {
                        const name = $(el).attr('name');
                        return name ? name.startsWith('pos_') : false;
                    });

                // Show the pos_config_id field if there are shown 'pos_*' fields.
                // But the search header has ugly bottom margin when the pos_config_id field is shown,
                // so we remove the bottom margin when the field is shown.
                const posSearchHeader = module.settingView.find('.settingSearchHeader');
                if (posConfigFields.length > 0) {
                    module.settingView.find('div#pos_header .o_setting_box').removeClass('o_hidden');
                    posSearchHeader.addClass('mb-0');
                } else {
                    posSearchHeader.removeClass('mb-0');
                }
            }
            return isModuleVisible;
        },
    });

    ResConfigSettings.Controller.include({
        _startRenderer() {
            return this._super.apply(this, arguments).then(result => {
                // Force tooltip to elements with `pos-data-bs-toggle="tooltip"` attribute.
                // We made it specific to ensure we don't interfere with other data-bs-toggle="tooltip" in the form.
                this.renderer.$('[pos-data-bs-toggle="tooltip"]').tooltip();
                return result;
            })
        }
    })

    return ResConfigSettings;
});
