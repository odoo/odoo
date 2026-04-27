from odoo import _, api, fields, models, Command
from ..api.swissdec_declarations import SwissdecDeclaration
from odoo.exceptions import ValidationError
import uuid

XSD_SKIP_VALUE = "XSDSKIP"

class L10nChDialogMessage(models.Model):
    _name = "l10n.ch.dialog.message"
    _description = "Swissdec Dialog Message"
    _order = "swissdec_creation desc"

    swissdec_job_id = fields.Many2one("l10n.ch.swissdec.job.result", required=True, readonly=True)
    notifications = fields.Json()
    status = fields.Selection(selection=[('Waiting', 'Waiting Reply'),
                                         ('Processing', 'Processing'),
                                         ('Finished', 'Finished')], default="Waiting")

    swissdec_creation = fields.Datetime(string="Creation Time", readonly=True)
    swissdec_story_id = fields.Char(string="Story ID", readonly=True)
    swissdec_StandardDialogID = fields.Char(readonly=True)
    swissdec_Previous = fields.Char(string="Previous Message", readonly=True)
    swissdec_Title = fields.Char(string="Title", readonly=True)
    swissdec_Description = fields.Char(string="Description", readonly=True)

    dialog_field_ids = fields.One2many("l10n.ch.dialog.message.field", 'dialog_message_id')

    def action_reply_dialog(self):
        self.ensure_one()
        self.swissdec_job_id._reply_dialog(self)

    def action_poll(self):
        self.ensure_one()
        self.swissdec_job_id._poll_dialog(self)

    def to_swissdec_dict(self):
        self.ensure_one()

        sections_map = {}
        for f in self.dialog_field_ids.filtered(lambda f: f.field_type == 'section'):
            sections_map[f.swissdec_section_id_ref] = {
                "sectionID": f.swissdec_section_id_ref,
                "Heading": f.swissdec_label,
            }
            if f.swissdec_value:
                sections_map[f.swissdec_section_id_ref].update({
                    "Description": f.swissdec_value,
                })


        paragraphs = []
        for f in self.dialog_field_ids.filtered(lambda x: x.field_type in ('value', 'answer')).sorted('sequence'):
            p_dict = {
                "ID": f.swissdec_id,
                "Label": f.swissdec_label,
            }
            if f.swissdec_section_id_ref:
                p_dict.update({
                    "sectionIDRef": f.swissdec_section_id_ref
                })


            if f.field_type == "answer":
                # Reconstruct the Answer block. We must consider Default and Value logic.
                a_type = f.swissdec_answer_value_type
                answer_block = {}
                if a_type:
                    # Retrieve default and value from fields
                    def_val = None
                    val_val = None

                    # Fetch defaults
                    if a_type == "String":
                        def_val = f.swissdec_answer_default_String
                        val_val = f.swissdec_answer_value_String
                    elif a_type == "Integer":
                        def_val = f.swissdec_answer_default_Integer
                        val_val = f.swissdec_answer_value_Integer
                    elif a_type == "Double":
                        def_val = f.swissdec_answer_default_Double
                        val_val = f.swissdec_answer_value_Double
                    elif a_type == "Boolean":
                        def_val = "true" if f.swissdec_answer_default_Boolean else "false"
                        val_val = "true" if f.swissdec_answer_value_Boolean else "false"
                    elif a_type == "Date":
                        def_val = f.swissdec_answer_default_Date.isoformat() + 'Z' if f.swissdec_answer_default_Date else False
                        val_val = f.swissdec_answer_value_Date.isoformat() + 'Z' if f.swissdec_answer_value_Date else False
                    elif a_type == "DateTime":
                        def_val = f.swissdec_answer_default_DateTime.isoformat() + 'Z' if f.swissdec_answer_default_DateTime else False
                        val_val = f.swissdec_answer_value_DateTime.isoformat() + 'Z' if f.swissdec_answer_value_DateTime else False
                    elif a_type == "YesNoUnknown":
                        def_val = f.swissdec_answer_default_YesNoUnknown
                        val_val = f.swissdec_answer_value_YesNoUnknown
                    elif a_type == "Amount":
                        def_val = SwissdecDeclaration.amount2str(f.swissdec_answer_default_Amount)
                        val_val = SwissdecDeclaration.amount2str(f.swissdec_answer_value_Amount)
                    elif a_type == "Problem":
                        pass


                    typed_block = {}
                    if val_val or a_type in ["Double", "Integer"]:
                        typed_block["Value"] = val_val
                    if (def_val or a_type in ["Double", "Integer"]) and f.swissdec_has_default:
                        typed_block["Default"] = def_val
                    if not val_val and def_val and f.swissdec_has_default:
                        typed_block["Value"] = def_val

                    if not typed_block:
                        if f.swissdec_answer_optional:
                            continue
                        else:
                            raise ValidationError(_("Some mandatory answers were not filled"))
                    answer_block[a_type] = typed_block or XSD_SKIP_VALUE

                    if f.swissdec_answer_optional:
                        # 'optional' attribute means we include it as empty attribute in the final dict
                        answer_block["optional"] = ""

                p_dict["Answer"] = answer_block

            paragraphs.append(p_dict)

        creation_iso = self.swissdec_creation.isoformat() if self.swissdec_creation else None
        final_dict = {
            "Creation": creation_iso,
            "StoryID": str(uuid.uuid4().hex),
            "StandardDialogID": self.swissdec_StandardDialogID,
            "Previous": {
                "ResponseStoryID": self.swissdec_story_id
            },
            "Title": self.swissdec_Title,
            "Description": self.swissdec_Description,
            "Section": list(sections_map.values()) if sections_map else None,
            "Paragraph": paragraphs,
        }

        return final_dict

    def action_open_dialog(self):
        return {
            'name': self.swissdec_Title,
            'res_model': 'l10n.ch.dialog.message',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'target': "current"
        }


class L10nChDialogMessageField(models.Model):
    _name = "l10n.ch.dialog.message.field"
    _description = "Swissdec Dialog Message Field"
    _order = "sequence, swissdec_id asc"

    dialog_message_id = fields.Many2one("l10n.ch.dialog.message", required=True)
    sequence = fields.Integer()
    field_type = fields.Selection(selection=[
        ('section', 'Section'),
        ('value', 'Value'),
        ('answer', 'Answer'),
    ])
    swissdec_id = fields.Char(readonly=True)
    swissdec_section_id_ref = fields.Char(readonly=True)
    swissdec_label = fields.Char()

    swissdec_value_type = fields.Selection([
        ("String", "String"),
        ("Integer", "Integer"),
        ("Double", "Double"),
        ("Boolean", "Boolean"),
        ("Date", "Date"),
        ("DateTime", "DateTime"),
        ("YesNoUnknown", "YesNoUnknown"),
        ("Amount", "Amount"),
        ("Problem", "Problem"),
    ])
    swissdec_value = fields.Char()

    # Answer fields
    swissdec_answer_value_type = fields.Selection([
        ("String", "String"),
        ("Integer", "Integer"),
        ("Double", "Double"),
        ("Boolean", "Boolean"),
        ("Date", "Date"),
        ("DateTime", "DateTime"),
        ("YesNoUnknown", "YesNoUnknown"),
        ("Amount", "Amount"),
        ("Problem", "Problem"),
    ])
    swissdec_answer_optional = fields.Boolean(default=False)

    # Default fields for Answer
    swissdec_has_default = fields.Boolean()
    swissdec_answer_default_String = fields.Char()
    swissdec_answer_default_Integer = fields.Integer()
    swissdec_answer_default_Double = fields.Float()
    swissdec_answer_default_Boolean = fields.Boolean()
    swissdec_answer_default_Date = fields.Date()
    swissdec_answer_default_DateTime = fields.Datetime()
    swissdec_answer_default_YesNoUnknown = fields.Selection([
        ("yes", "Yes"),
        ("no", "No"),
        ("unknown", "Unknown")
    ])
    swissdec_answer_default_Amount = fields.Float()

    # Value fields for Answer
    swissdec_answer_value_String = fields.Char()
    swissdec_answer_value_Integer = fields.Integer()
    swissdec_answer_value_Double = fields.Float()
    swissdec_answer_value_Boolean = fields.Boolean()
    swissdec_answer_value_Date = fields.Date()
    swissdec_answer_value_DateTime = fields.Datetime()
    swissdec_answer_value_YesNoUnknown = fields.Selection([
        ("yes", "Yes"),
        ("no", "No"),
        ("unknown", "Unknown")
    ])
    swissdec_answer_value_Amount = fields.Float()
