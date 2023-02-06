/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 *
 */
export const productConfiguratorService = {
    start(env) {
        this.currentProductConfigurator = undefined;
        this.productConfigurationStack = [];

        const callConfigurator = async () => {
            const configurator = this.productConfigurationStack.shift();
            this.currentProductConfigurator = configurator;
            await configurator();

            if (this.productConfigurationStack.length !== 0){
                await callConfigurator();
            } else {
                this.currentProductConfigurator = undefined;
            }
        }

        const configureProduct = async (configureProduct) => {
            this.productConfigurationStack.push(configureProduct);

            if (!this.currentProductConfigurator) {
                callConfigurator();
            }
        }

        const productConfiguratorService = {
            configureProduct,
        };

        return productConfiguratorService;
    }
};

registry.category("services").add("saleProductConfiguratorService", productConfiguratorService);
