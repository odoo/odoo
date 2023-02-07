/* @odoo-module */

import { Record } from '@web/views/relational_model';
import { session } from '@web/session';
import { x2ManyCommands } from "@web/core/orm_service";
import { WarningDialog } from "@web/core/errors/error_dialogs";

export class ProjectTaskRecord extends Record {
    async _applyChanges(changes) {
        const value = changes.personal_stage_type_ids;
        if (value && Array.isArray(value)) {
            delete changes.personal_stage_type_ids;
            changes.personal_stage_type_id = value;
        }
        await super._applyChanges(changes);
    }

    get context() {
        const context = super.context;
        const value = context.default_personal_stage_type_ids;
        if (value && Array.isArray(value)) {
            context.default_personal_stage_type_id = value[0];
            delete context.default_personal_stage_type_ids;
        }
        return context;
    }

    modifyName(changes, new_values, element) {
        new_values['name'] = `${new_values['name']} ${element}`;
    }

    modifyOtherFields(changes, new_values, element) {
        this.modifyName(...arguments);
    }

//#region Quick Create Task with shortcuts
    options = {
        '+': (param, changes, errors) => {
            if (!param)
                this.addShortcutError(`+${param}`, errors);
            else
                this.addM2mOption('tags', param, changes);
        },
        '@': (param, changes, errors) => {
            if (!!param.localeCompare('me', undefined, { sensitivity: 'base' }))
                this.addShortcutError(`@${param}`, errors);
            else
                this.addM2mOption('user_ids', x2ManyCommands.linkTo(session.uid), changes);
        },
        '*': (param, changes, errors) => {
            if (!!param)
                this.addShortcutError(`*${param}`, errors);
            else
                this.addOption('priority', '1', changes);
        },
    }

    openQuickCreateWarningModal(message) {
        this.model.dialogService.add(WarningDialog, {
            title: this.model.env._t("Task Quick Creation Failed"),
            message: this.model.env._t(message),
        });
    }

    addShortcutError(option, errors) {
        errors.push(`${option} is not a valid option`);
    }

    addM2mOption(option, param, changes) {
        if (!changes.hasOwnProperty(option))
            changes[option] = [param];
        else if (!changes[option].map(x => JSON.stringify(x).toUpperCase()).includes(JSON.stringify(param).toUpperCase())) {
            changes[option].push(param);
        }
    }

    addOption(option, param, changes) {
        changes[option] = param;
    }

    isEndOfOption(index, params, options) {
        return index === params.length -1 ||
            params[index] === ' ' && index+1<params.length && options.includes(params[index+1]);
    }

    async _save() {
        const changes = this.getChanges();
        if (changes.name) {
            const possibleOptions = Object.keys(this.options);
            if (possibleOptions.includes(changes.name[0]))
                return this.openQuickCreateWarningModal(`${possibleOptions} are not allowed at the start of the title`);

            let name = '';
            let index;
            for (index=0 ; index<changes.name.length ; index++) {
                if (this.isEndOfOption(index, changes.name, possibleOptions))
                    break;
                name += changes.name[index];
            }
            let params = changes.name.slice(index+1);
            changes.name = name;

            if (!!params) {
                let param = '';
                let option = params[0];
                let errors = [];
                for (index=1 ; index<params.length; index++) {
                    if (this.isEndOfOption(index, params, possibleOptions)) {
                        if (index === params.length-1)
                            param += params[index];
                        this.options[option](param, changes, errors);
                        option = params[++index];
                        param = '';
                    } else
                        param += params[index];
                }

                if (!!errors.length)
                    return this.openQuickCreateWarningModal(errors.join('\n'));

                if (!!changes['tags'].length) {
                    const domain = changes['tags'].map(tag => ['name', '=ilike', tag]);
                    domain.unshift(...Array(domain.length-1).fill('|'));
                    const existing_tags = await this.model.orm.call("project.tags", "search_read", [domain]);
                    const existing_tags_names = existing_tags.map(({name}) => name);
                    const tags_to_create = changes['tags'].filter(tag => !existing_tags_names.includes(tag));
                    changes['tag_ids'] = existing_tags.map(({id}) => x2ManyCommands.linkTo(id));
                    changes['tag_ids'] = changes['tag_ids'].concat(tags_to_create.map(tag => x2ManyCommands.create(false, { 'name': tag })));
                    delete changes['tags'];
                }
            }
        }
        return await super._save(...arguments, changes);
    }
//#endregion
}
