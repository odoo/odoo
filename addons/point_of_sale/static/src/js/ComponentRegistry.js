odoo.define('point_of_sale.ComponentRegistry', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ClassRegistry = require('point_of_sale.ClassRegistry');

    class ComponentRegistry extends ClassRegistry {
        freeze() {
            super.freeze();
            // Make sure PosComponent has the compiled classes.
            // This way, we don't need to explicitly declare that
            // a set of components is children of another.
            PosComponent.components = {};
            for (let [base, compiledClass] of this.cache.entries()) {
                PosComponent.components[base.name] = compiledClass;
            }
        }
        _recompute(base, old) {
            const res = super._recompute(base, old);
            if (typeof base === 'string') {
                base = this.baseNameMap[base];
            }
            PosComponent.components[base.name] = res;
            return res;
        }
    }

    return ComponentRegistry;
});
