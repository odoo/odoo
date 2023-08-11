/** @odoo-module **/

    /**
     * This file defines the common environment, which contains everything that
     * is needed in the env for both the backend and the frontend (Odoo
     * terminology). This module shouldn't be used as is. It should only be
     * imported by the module defining the final env to use (in the frontend or
     * in the backend). For instance, module 'web.env' imports it, adds stuff to
     * it, and exports the final env that is used by the whole webclient
     * application.
     *
     * There should be as much dependencies as possible in the env object. This
     * will allow an easier testing of components. See [1] for more information
     * on environments.
     *
     * [1] https://github.com/odoo/owl/blob/master/doc/reference/environment.md#content-of-an-environment
     */

    import { bus } from "@web/legacy/js/services/core";

    // Build the basic env
    const env = {
        bus,
        debug: odoo.debug,
        services: {},
    };

    export default env;
