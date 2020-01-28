odoo.define('web.AbstractService', function (require) {
'use strict';

const env = require('web.env');

class AbstractService {
    /**
     * @abstract
     */
    start() {}
}

Object.assign(AbstractService, {
    env,
    dependencies: [],
});

return AbstractService;
});
