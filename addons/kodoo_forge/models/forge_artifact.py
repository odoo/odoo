from odoo import fields, models


class ForgeArtifact(models.Model):
    _name = "forge.artifact"
    _description = "Forge Artifact"

    build_id = fields.Many2one("forge.build", required=True, ondelete="cascade")
    file_path = fields.Char(
        required=True, help="Relative path within generated module"
    )
    content = fields.Text()
    content_hash = fields.Char(help="SHA256 of content at generation time")
    model_hash = fields.Char(help="SHA256 of forge model state at generation time")
    artifact_type = fields.Selection(
        [
            ("manifest", "Manifest"),
            ("model", "Model"),
            ("view", "View"),
            ("security", "Security"),
            ("data", "Data"),
            ("automation", "Automation"),
            ("test", "Test"),
        ]
    )
