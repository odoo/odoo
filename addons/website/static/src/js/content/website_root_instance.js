odoo.define('root.widget', function (require) {
'use strict';

const AbstractService = require('web.AbstractService');
const env = require('web.public_env');
var lazyloader = require('web.public.lazyloader');
var websiteRootData = require('website.root');

/**
 * Configure Owl with the public env
 */
owl.config.mode = env.isDebug() ? "dev" : "prod";
owl.Component.env = env;

/**
 * Deploy services in the env
 */
AbstractService.prototype.deployServices(env);

var websiteRoot = new websiteRootData.WebsiteRoot(null);
return lazyloader.allScriptsLoaded.then(function () {
    return websiteRoot.attachTo(document.body).then(function () {
        return websiteRoot;
    });
});
});
