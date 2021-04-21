/** @odoo-module **/

import useStore from '@mail/component_hooks/use_store/use_store';

const { Component } = owl;

class Category extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const category = this.env.models['mail.category'].get(props.categoryLocalId);
            return {
                category: category ? category.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    get category() {
        return this.env.models['mail.category'].get(this.props.categoryLocalId);
    }

}

Object.assign(Category, {
    props: {
        categoryLocalId: String,
    },
    template: 'mail.Category',
});

export default Category;
