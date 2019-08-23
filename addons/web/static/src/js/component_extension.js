/**
 * Add a new method to owl Components to ensure that no performed RPC is
 * resolved/rejected when the component is destroyed.
 */
(function () {
    owl.Component.prototype.rpc = function () {
        return new Promise((resolve, reject) => {
            return this.env.services.rpc(...arguments)
                .then(result => {
                    if (!this.__owl__.isDestroyed) {
                        resolve(result);
                    }
                })
                .catch(reason => {
                    if (!this.__owl__.isDestroyed) {
                        reject(reason);
                    }
                });
        });
    };
})();
