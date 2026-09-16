from odoo.db.schema import column_exists


def migrate(cr, version):
    if not version or not column_exists(cr, "approval_observation", "model_name"):
        return
    cr.execute(
        """
        UPDATE approval_observation observation
           SET model_name = COALESCE(observation.model_name, binding.model_name),
               operation = COALESCE(observation.operation, binding.method, 'unknown')
          FROM approval_binding binding
         WHERE binding.id = observation.binding_id
           AND (observation.model_name IS NULL OR observation.operation IS NULL)
        """
    )
    cr.execute(
        """
        DELETE FROM approval_observation
         WHERE model_name IS NULL OR operation IS NULL
        """
    )
