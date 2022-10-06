odoo.define('web.view_registry', function (require) {
"use strict";

/**
 * This module defines the view_registry. Web views are added to the registry
 * in the 'web._view_registry' module to avoid cyclic dependencies.
 * Views defined in other addons should be added in this registry as well,
 * ideally in another module than the one defining the view, in order to
 * separate the declarative part of a module (the view definition) from its
 * 'side-effects' part.
 */

var Registry = require('web.Registry');

return new Registry();

});
