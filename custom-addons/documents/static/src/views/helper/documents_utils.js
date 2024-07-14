/** @odoo-module */

export default {
    async get_link_proportion(orm, documents_ids = false, domain = false){
        if (!domain && !documents_ids) {
            return 'none';
        }
        const read_domain = documents_ids.length ? [['id', 'in', documents_ids]] : domain;
        const result = await orm.readGroup(
            'documents.document',
            read_domain,
            [],
            ['type']
        );
        if (!result){
            return 'none'
        }
        if (result.every(document => document['type'] == 'url')){
            return 'all'
        }
        else if (result.some(document => document['type'] == 'url')) {
            return 'some'
        }
        return 'none'
    },
};
