odoo.define('pos_paytm.chrome', function (require) {
    'use strict';

    const core = require('web.core');
    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    const _t = core._t;

    const PosPaytmChrome = (Chrome) =>
        class extends Chrome {
        	//Need to override this to handle Error thrown on request Exception or missing payment provider
            errorHandler(env, error, originalError) {
            	if(originalError?.message?.data?.message === "Unable to establish connection with PayTM." ||
                    originalError?.message?.data?.message === "PayTM payment provider is missing") {
            		return true;
            	}
            	return super.errorHandler(env, error, originalError);
        	}
        };

    Registries.Component.extend(Chrome, PosPaytmChrome);

    return PosPaytmChrome;
});
