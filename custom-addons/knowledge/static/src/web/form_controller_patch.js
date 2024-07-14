/** @odoo-module */

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { CallbackRecorder } from "@web/webclient/actions/action_hook";
import {
    useEffect,
    useSubEnv
} from "@odoo/owl";


/**
 * Knowledge articles can interact with some records with the help of the
 * @see KnowledgeCommandsService if they have an html field.
 * The algorithm first searches for an html field name in the following list.
 * The list is ordered and the first match found in a record will take
 * precedence. If no match is found, any accessible html field in the view
 * will do, in order of declaration.
 * Once a match is found, it is stored in the
 * KnowledgeCommandsService to be accessed later by an article.
 * If the field is inside a Form notebook page, the page must have a name
 * attribute, or else it won't be considered as Knowledge macros won't be able
 * to access it through a selector.
 */
const KNOWLEDGE_RECORDED_FIELD_NAMES = [
    'note',
    'memo',
    'description',
    'comment',
    'narration',
    'additional_note',
    'internal_notes',
    'notes',
];

/**
 * Here are the models whose html fields won't be accessible through Knowledge.
 * A consideration to add a model in this list is how heavily modified their
 * form view is compared to the standard, because then the macro will not be
 * able to navigate them.
 */
const KNOWLEDGE_EXCLUDED_MODELS = new Set([
    'knowledge.article',
    'res.config.settings',
]);

const FormControllerPatch = {
    setup() {
        super.setup(...arguments);
        this.command = useService("command");
        if (!this.env.inDialog) {
            this.knowledgeCommandsService = useService('knowledgeCommandsService');
            useSubEnv({
                __knowledgeUpdateCommandsRecordInfo__: new CallbackRecorder(),
            });
            useEffect(
                () => this._evaluateRecordCandidate(),
                () => [this.model.root.resId],
            );
        }
    },
    /**
     * Evaluate the current record and register its relevant information in
     * @see KnowledgeCommandsService if it can be used in a Knowledge article
     * through a macro.
     *
     * The access rights information for the chatter is only available
     * asynchronously after it is mounted, therefore populating this
     * information for the `commandsRecordInfo` is delegated to the chatter
     * through the __knowledgeUpdateCommandsRecordInfo__ callbackRecorder.
     */
    _evaluateRecordCandidate() {
        if (
            KNOWLEDGE_EXCLUDED_MODELS.has(this.props.resModel) ||
            !this.env.config.breadcrumbs ||
            !this.env.config.breadcrumbs.length
        ) {
            return;
        }

        const record = this.model.root;
        const fields = this.props.fields;
        const xmlDoc = this.props.archInfo.xmlDoc;
        // format stored by the knowledgeCommandsService
        const commandsRecordInfo = {
            resId: this.model.root.resId,
            resModel: this.props.resModel,
            breadcrumbs: this.knowledgeCommandsService.getBreadcrumbsIdentifier(
                this.env.config.breadcrumbs || []
            ),
            canPostMessages: false,
            canAttachFiles: false,
            withHtmlField: false,
            fieldInfo: {},
            xmlDoc: this.props.archInfo.xmlDoc,
        };

        // check whether the form view has a chatter
        if (this.props.archInfo.xmlDoc.querySelector('.oe_chatter')) {
            for (const callback of this.env.__knowledgeUpdateCommandsRecordInfo__.callbacks) {
                callback(commandsRecordInfo);
            }
        }

        if (this.props.mode === "readonly" || !this.canEdit) {
            return;
        }

        const defaultFieldNamesSet = new Set(KNOWLEDGE_RECORDED_FIELD_NAMES);
        const fieldNames = KNOWLEDGE_RECORDED_FIELD_NAMES.filter((name) => {
            return (
                name in record.activeFields &&
                fields[name].type === "html" &&
                !fields[name].readonly
            );
        }).concat(
            Object.getOwnPropertyNames(record.activeFields).filter((name) => {
                return (
                    !defaultFieldNamesSet.has(name) &&
                    fields[name].type === "html" &&
                    !fields[name].readonly
                );
            })
        );

        // check if there is any html field usable with knowledge
        loopFieldNames: for (const fieldName of fieldNames) {
            if (
                evaluateBooleanExpr(record.activeFields[fieldName].readonly, record.evalContextWithVirtualIds) ||
                evaluateBooleanExpr(record.activeFields[fieldName].invisible, record.evalContextWithVirtualIds)
            ) {
                continue loopFieldNames;
            }
            // Parse the xmlDoc to find all instances of the field that are
            // not descendants of another field and whose parents are
            // visible (relative to the current record's context). Evaluate
            // the invisible and readonly modifiers attributes for each field
            // instance in the xmlDoc. Don't consider html fields that are not
            // using the `html` widget (i.e. mass_mailing_html widget).
            const xmlFields = Array.from(xmlDoc.querySelectorAll(`field[name="${fieldName}"]:is([widget="html"], :not([widget])`));
            const xmlFieldsCandidates = xmlFields.filter((xmlField) => {
                return (
                    !(xmlField.parentElement.closest('field')) &&
                    !evaluateBooleanExpr(xmlField.getAttribute('readonly'), record.evalContextWithVirtualIds) &&
                    !evaluateBooleanExpr(xmlField.getAttribute('invisible'), record.evalContextWithVirtualIds)
                );
            });
            loopXmlFieldsCandidates: for (const xmlField of xmlFieldsCandidates) {
                const xmlFieldParent = xmlField.parentElement;
                let xmlInvisibleParent = xmlFieldParent.closest('[invisible]');
                while (xmlInvisibleParent) {
                    const invisibleParentModifier = xmlInvisibleParent.getAttribute('invisible');
                    if (evaluateBooleanExpr(invisibleParentModifier, record.evalContextWithVirtualIds)) {
                        continue loopXmlFieldsCandidates;
                    }
                    xmlInvisibleParent = xmlInvisibleParent.parentElement &&
                        xmlInvisibleParent.parentElement.closest('[invisible]');
                }
                const page = xmlField.closest('page');
                const pageName = page ? page.getAttribute('name') : undefined;
                // If the field is inside an unnamed notebook page, ignore
                // it as if it was unavailable, since the macro will not be
                // able to open it to access the field (the name is used as
                // a selector).
                if (!page || pageName) {
                    commandsRecordInfo.fieldInfo = {
                        name: fieldName,
                        string: fields[fieldName].string,
                        pageName: pageName,
                    };
                    break loopFieldNames;
                }
            }
        }
        if (commandsRecordInfo.fieldInfo.name) {
            commandsRecordInfo.withHtmlField = true;
        }
        if (this.knowledgeCommandsService.isRecordCompatibleWithMacro(commandsRecordInfo)) {
            this.knowledgeCommandsService.setCommandsRecordInfo(commandsRecordInfo);
        }
    },
    async onClickSearchKnowledgeArticle() {
        if (await this.model.root.isDirty() || this.model.root.isNew) {
            const saved = await this.model.root.save();
            if (!saved) {
                return;
            }
        }
        this.command.openMainPalette({ searchValue: "?" });
    },
};

patch(FormController.prototype, FormControllerPatch);
