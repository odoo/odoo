odoo.define('web.config', function (require) {
"use strict";

/**
 * This module contains all the (mostly) static 'environmental' information.
 * This is often necessary to allow the rest of the web client to properly
 * render itself.
 *
 * Note that many informations currently stored in session should be moved to
 * this file someday.
 */

var core = require('web.core');

var config = {
    /**
     * debug is a boolean flag.  It is only considered true if the flag is set
     * in the url
     */
    debug: ($.deparam($.param.querystring()).debug !== undefined),
    device: {
        /**
         * touch is a boolean, true if the device supports touch interaction
         */
        touch: 'ontouchstart' in window || 'onmsgesturechange' in window,
        /**
         * size_class is an integer: 0, 1, 2 or 3, depending on the (current)
         * size of the device.  This is a dynamic property, updated whenever the
         * browser is resized
         */
        size_class: null,
        /**
         * A frequent use case is to have a different render in 'mobile' mode,
         * meaning when the screen is small.  This flag (boolean) is true when
         * the size is not 3.  It is also updated dynamically.
         */
        isMobile: null,
        /**
         * Mapping between the numbers 0,1,2,3 and some descriptions
         */
        SIZES: { XS: 0, SM: 1, MD: 2, LG: 3 },
    },
};


var medias = [
    window.matchMedia('(max-width: 767px)'),
    window.matchMedia('(min-width: 768px) and (max-width: 991px)'),
    window.matchMedia('(min-width: 992px) and (max-width: 1199px)'),
    window.matchMedia('(min-width: 1200px)')
];

/**
 * Return the current size class
 *
 * @returns {integer} a number between 0 and 3, included
 */
function _getSizeClass() {
    for(var i = 0 ; i < medias.length ; i++) {
        if(medias[i].matches) {
            return i;
        }
    }
}
/**
 * Update the size dependant properties in the config object.  This method
 * should be called every time the size class changes.
 */
function _updateSizeProps() {
    var sc = _getSizeClass();
    if (sc !== config.device.size_class) {
        config.device.size_class = sc;
        config.isMobile = config.device.size_class <= config.device.SIZES.XS;
        core.bus.trigger('size_class', sc);
    }
}

_.invoke(medias, 'addListener', _updateSizeProps);
_updateSizeProps();

return config;

});
