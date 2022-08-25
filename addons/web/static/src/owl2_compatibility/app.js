(function () {
    const App = owl.App;

    // templates' code is shared between multiple instances of Apps
    // This is useful primarly for the OWL2 to Legacy compatibility layer
    // It is also useful for tests.
    // The downside of this is that the compilation is done once with the compiling app's
    // translate function and attributes.
    const sharedTemplates = {};

    owl.App = class extends App {
        constructor(_, config) {
            if (!config.test) {
                const missingKeys = ["dev", "translateFn", "translatableAttributes"].filter(
                    (key) => !(key in config)
                );
                if (missingKeys.length) {
                    throw new Error(
                        `Attempted to create an App without some required key(s) (${missingKeys.join(
                            ", "
                        )})`
                    );
                }
            }
            super(...arguments);
        }
        _compileTemplate(name) {
            if (!(name in sharedTemplates)) {
                sharedTemplates[name] = super._compileTemplate(...arguments);
            }
            return sharedTemplates[name];
        }
    };
    owl.App.sharedTemplates = sharedTemplates;
    owl.App.validateTarget = () => {};
})();
