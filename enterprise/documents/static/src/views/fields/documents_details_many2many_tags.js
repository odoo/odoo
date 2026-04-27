import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

/**
 * @override update, quickCreate (also called with create&Edit), and deleteTag
 * to save the record in db immediately. This is necessary to edit records
 * that are not "selected" as when they are inspected on the details panel when
 * in "preview" mode.
 */
export class DocumentsDetailsMany2ManyTagsField extends Many2ManyTagsField {

    setup() {
        super.setup();
        const superUpdate = this.update;
        this.update = (recordlist) => {
            const ret = superUpdate(recordlist);
            this.props.record.save();
            return ret;
        };
        if (this.quickCreate) {
            const superQuickCreate = this.quickCreate;
            this.quickCreate = async (name) => {
                const ret = await superQuickCreate(name);
                this.props.record.save();
                return ret;
            };
        }
    }

    async deleteTag(id) {
        await super.deleteTag(id);
        await this.props.record.save();
    }
}
