odoo.define('root.widget', function (require) {
'use strict';

const AbstractService = require('web.AbstractService');
const env = require('web.public_env');
var lazyloader = require('web.public.lazyloader');
var rootData = require('web.public.root');

/**
 * Configure Owl with the public env
 */
owl.config.mode = env.isDebug() ? "dev" : "prod";
owl.Component.env = env;

/**
 * Deploy services in the env
 */
AbstractService.prototype.deployServices(env);

/**
 * This widget is important, because the tour manager needs a root widget in
 * order to work. The root widget must be a service provider with the ajax
 * service, so that the tour manager can let the server know when tours have
 * been consumed.
 */
var publicRoot = new rootData.PublicRoot(null);
return lazyloader.allScriptsLoaded.then(function () {
    return publicRoot.attachTo(document.body).then(function () {
        return publicRoot;
    });
});

});
