import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { useSubEnv } from "@odoo/owl";

export const DocumentsControllerMixin = (component) =>
    class extends component {
        setup() {
            super.setup(...arguments);
            this.searchBarToggler = useSearchBarToggler();
            useSubEnv({
                searchBarToggler: this.searchBarToggler,
            });
        }

        get modelParams() {
            const modelParams = super.modelParams;
            // Temporary fix to add fields to view. todo: remove in master
            const knownDescriptions = {
                bool: { ...modelParams.config.activeFields.is_access_via_link_hidden },
                char: { ...modelParams.config.activeFields.name },
                m2o: { ...modelParams.config.activeFields.owner_id },
                m2m: { ...modelParams.config.activeFields.tag_ids },
            };
            Object.assign(modelParams.config.activeFields, {
                alias_domain_id:
                    modelParams.config.activeFields.alias_domain_id || knownDescriptions.m2o,
                alias_name: modelParams.config.activeFields.alias_name || knownDescriptions.char,
                alias_tag_ids:
                    modelParams.config.activeFields.alias_tag_ids || knownDescriptions.m2m,
                create_activity_user_id:
                    modelParams.config.activeFields.create_activity_user_id ||
                    knownDescriptions.m2o,
                create_activity_type_id:
                    modelParams.config.activeFields.create_activity_type_id ||
                    knownDescriptions.m2o,
                file_size: modelParams.config.activeFields.file_size || {
                    ...modelParams.config.activeFields.id,
                }, // readonly int
                is_pinned_folder: modelParams.config.activeFields.is_pinned_folder || {
                    ...knownDescriptions.bool,
                },
                res_name: modelParams.config.activeFields.res_name || {
                    ...knownDescriptions.char,
                    readonly: true,
                },
            });
            modelParams.multiEdit = true;
            return modelParams;
        }
    };
