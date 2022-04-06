/** @odoo-module **/

import { KnowledgeArticleFormController } from '@knowledge/js/knowledge_controller';

KnowledgeArticleFormController.include({
    /**
     * @override
     * @returns {Array[String]}
     */
    _getFieldsToForceSave: function () {
        return this._super().concat('website_published');
    },
});
