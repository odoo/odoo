
export class StripeOptions {
    /**
     * Prepare the options to init the Stripe JS Object.
     *
     * This method serves as a hook for modules that would fully implement Stripe Connect.
     *
     * @param {object} processingValues
     * @return {object}
     */
    _prepareStripeOptions(processingValues) {
        const locale = document.documentElement.lang;
        return {
            ...(locale ? { locale } : {}),  // Default to browser locale if not set.
        };
    };
}
