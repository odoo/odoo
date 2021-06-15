/** @odoo-module **/

const { Component, tags } = owl;

export function makeNonUpdatableComponent(Comp) {
    class NoUpdate extends Component {
        shouldUpdate() {
            return false;
        }
    }
    NoUpdate.template = tags.xml`<t t-component="Comp" t-props="props"/>`;
    NoUpdate.components = { Comp };

    return NoUpdate;
}
