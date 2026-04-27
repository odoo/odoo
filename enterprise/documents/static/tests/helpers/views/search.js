export function getEnrichedSearchArch(searchArch = "<search></search>") {
    const searchPanelArch = `
        <searchpanel class="o_documents_search_panel">
            <field name="folder_id" string="Folders"/>
        </searchpanel>
    `;
    return searchArch.split("</search>")[0] + searchPanelArch + "</search>";
}
