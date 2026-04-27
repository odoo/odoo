import { getEnrichedSearchArch } from "@documents/../tests/helpers/views/search";
import { mountView } from "@web/../tests/web_test_helpers";

export const basicDocumentsKanbanArch = /* xml */ `
<kanban js_class="documents_kanban">
    <templates>
        <field name="id"/>
        <field name="available_embedded_actions_ids"/>
        <field name="access_token"/>
        <field name="mimetype"/>
        <field name="folder_id"/>
        <field name="owner_id"/>
        <field name="partner_id"/>
        <field name="user_permission"/>
        <field name="active"/>
        <field name="type"/>
        <field name="attachment_id"/>
        <t t-name="card">
            <div>
                <div name="document_preview" class="o_kanban_image_wrapper">a thumbnail</div>
                <i class="fa fa-circle o_record_selector"/>
                <field name="name"/>
            </div>
        </t>
    </templates>
</kanban>
`;

export async function mountDocumentsKanbanView(params = {}, target = null) {
    return mountView(
        {
            type: "kanban",
            resModel: "documents.document",
            arch: basicDocumentsKanbanArch,
            searchViewArch: getEnrichedSearchArch(),
            ...params,
        },
        target
    );
}
